"""
Recommendation Inference Service
---------------------------------
Thin orchestration layer: takes a user profile, calls a local LLM
(via Ollama's OpenAI-compatible API), and returns validated,
structured movie recommendations.

Endpoints:
  GET  /health                      - liveness check
  POST /recommendations/generate    - synchronous, user-facing
"""

import os
import json
import logging
from datetime import datetime, timezone
from functools import wraps

import requests
import jwt
from jwt import PyJWKClient
from flask import Flask, request, jsonify
from jsonschema import validate, ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inference-service")

app = Flask(__name__)


# ================================================================================================ #
# ========== Configuration ======================================================================= #
# ================================================================================================ #
PORT = int(os.environ.get("PORT", 8000))

# Internal Services
PROFILES_SERVICE_URL = os.environ.get("PROFILES_SERVICE_URL", "http://profiles-service:3000")
MOVIES_SERVICE_URL = os.environ.get("MOVIES_SERVICE_URL", "http://movies-service:3001")

# Ollama service
MODEL_SERVER_URL = os.environ.get("MODEL_SERVER_URL")
MODEL_NAME = os.environ.get("MODEL_NAME", "llama3.2:1b")
MAX_LLM_RETRIES = int(os.environ.get("MAX_LLM_RETRIES", 2))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", 600))

# Candidate retrieval settings
CANDIDATE_LIMIT = int(os.environ.get("CANDIDATE_LIMIT", 30))
CANDIDATE_MIN_RATING = float(os.environ.get("CANDIDATE_MIN_RATING", 7.0))

# Security / Keycloak Configuration
KEYCLOAK_JWKS_URL = os.environ.get("KEYCLOAK_JWKS_URL")
KEYCLOAK_ISSUER = os.environ.get("KEYCLOAK_ISSUER")
AUDIENCE = os.environ.get("AUDIENCE")
DISABLE_AUTH = os.environ.get("DISABLE_AUTH", "false").lower() in ("true", "1", "yes")

jwks_client = PyJWKClient(KEYCLOAK_JWKS_URL) if KEYCLOAK_JWKS_URL else None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if app.config.get("TESTING") or DISABLE_AUTH:
            request.token_payload = {"sub": "test-user"}
            return f(*args, **kwargs)

        if not jwks_client:
            logger.warning("Auth is required but KEYCLOAK_JWKS_URL is not set.")
            return jsonify({"error": "Auth service not configured"}), 500

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ")[1]

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            decode_options = {"verify_aud": bool(AUDIENCE)}

            kwargs_jwt = {
                "jwt": token,
                "key": signing_key.key,
                "algorithms": ["RS256"],
                "options": decode_options,
            }
            if AUDIENCE:
                kwargs_jwt["audience"] = AUDIENCE
            if KEYCLOAK_ISSUER:
                kwargs_jwt["issuer"] = KEYCLOAK_ISSUER

            request.token_payload = jwt.decode(**kwargs_jwt)

        except Exception as exc:
            logger.warning("Token verification failed: %s", exc)
            return jsonify({"error": "Unauthorized: Invalid or expired token"}), 401

        return f(*args, **kwargs)

    return decorated


# ================================================================================================ #
# ========== Schema for validating LLM output ==================================================== #
# ================================================================================================ #
RECOMMENDATION_SCHEMA = {
    "type": "object",
    "required": ["recommendations"],
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "year", "genres", "reason", "confidence"],
                "properties": {
                    "title": {"type": "string"},
                    "year": {"type": "integer"},
                    "genres": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
}


# ================================================================================================ #
# ========== Helpers ============================================================================= #
# ================================================================================================ #
def filter_and_prune_candidates(candidates: list, profile: dict) -> list[dict]:
    """
    Filters out watched movies and disliked genres, and prunes each movie to
    essential fields: {"title": m.title, "year": m.release_year, "genres": m.genres}.
    """
    watched_titles = set()
    for item in (profile.get("watch_history") or []):
        if isinstance(item, dict):
            t = item.get("title") or item.get("name")
        elif isinstance(item, (str, int, float)):
            t = str(item)
        else:
            t = None
        if t is not None:
            t_clean = str(t).strip().lower()
            if t_clean:
                watched_titles.add(t_clean)

    disliked_raw = profile.get("disliked_genres") or []
    if isinstance(disliked_raw, str):
        disliked_list = [g.strip() for g in disliked_raw.split(",") if g.strip()]
    elif isinstance(disliked_raw, (list, tuple, set)):
        disliked_list = [str(g).strip() for g in disliked_raw if str(g).strip()]
    else:
        disliked_list = []
    disliked_genres = {g.lower() for g in disliked_list}

    seen_titles = set()
    pruned = []

    for m in (candidates or []):
        if not isinstance(m, dict):
            continue
        title = m.get("title")
        if title is None:
            continue

        title_clean = str(title).strip()
        if not title_clean:
            continue

        title_lower = title_clean.lower()

        # 1. Deduplicate by title
        if title_lower in seen_titles:
            continue

        # 2. Exclude watched movies (case-insensitive title check)
        if title_lower in watched_titles:
            continue

        # 3. Exclude movies matching any genre in disliked_genres
        raw_genres = m.get("genres")
        if isinstance(raw_genres, str):
            genre_items = [g.strip() for g in raw_genres.split(",") if g.strip()]
        elif isinstance(raw_genres, (list, tuple, set)):
            genre_items = [str(g).strip() for g in raw_genres if str(g).strip()]
        else:
            genre_items = []

        movie_genres = {g.lower() for g in genre_items}
        if disliked_genres and (movie_genres & disliked_genres):
            continue

        year = m.get("release_year")
        if year is None:
            year = m.get("year")
        try:
            year = int(year) if year is not None else None
        except (ValueError, TypeError):
            year = None

        seen_titles.add(title_lower)
        pruned.append({
            "title": title_clean,
            "year": year,
            "genres": genre_items,
        })

    return pruned


def fetch_candidate_movies(profile: dict, headers: dict | None = None) -> list[dict]:
    """
    Queries movies-service for candidates matching user profile preferences,
    filters out watched and disliked movies, prunes to minimal fields,
    and returns a bounded pool of at most 30 movies.
    """
    req_headers = {}
    if headers and "Authorization" in headers:
        req_headers["Authorization"] = headers["Authorization"]

    raw_favs = profile.get("favorite_genres") or []
    if isinstance(raw_favs, str):
        fav_list = [g.strip() for g in raw_favs.split(",") if g.strip()]
    elif isinstance(raw_favs, (list, tuple, set)):
        fav_list = [str(g).strip() for g in raw_favs if str(g).strip()]
    else:
        fav_list = []

    min_year = profile.get("min_year")
    try:
        min_year = int(min_year) if min_year is not None else None
    except (ValueError, TypeError):
        min_year = None

    params = {
        "limit": CANDIDATE_LIMIT,
        "sort_by": "rating",
        "order": "desc",
        "min_rating": CANDIDATE_MIN_RATING,
    }
    if fav_list:
        params["genres"] = ",".join(fav_list)
    if min_year is not None:
        params["min_year"] = min_year

    movies = []
    try:
        resp = requests.get(
            f"{MOVIES_SERVICE_URL}/movies",
            headers=req_headers,
            params=params,
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            movies = data.get("movies", [])
        else:
            logger.warning("movies-service returned status %s: %s", resp.status_code, resp.text)
    except requests.RequestException as exc:
        logger.warning("Failed to query movies-service with profile filters: %s", exc)

    # Filter out watched movies and disliked genres, and prune to essential fields
    candidates = filter_and_prune_candidates(movies, profile)
    return candidates[:CANDIDATE_LIMIT]


def build_prompt(profile: dict, candidates: list, user_message: str | None) -> str:
    """
    Generates the prompt (to send to AI model), based on:
    - The user's profile
    - Movie candidates
    - Optionally, a custom user message
    """
    # Ensure candidates in prompt are strictly pruned to essential fields and bounded <= 30
    pruned_candidates = []
    for m in (candidates or [])[:30]:
        if isinstance(m, dict):
            title_val = str(m.get("title") or "").strip()
            if not title_val:
                continue

            y = m.get("year") if m.get("year") is not None else m.get("release_year")
            try:
                year_val = int(y) if y is not None else None
            except (ValueError, TypeError):
                year_val = None

            raw_g = m.get("genres")
            if isinstance(raw_g, str):
                g_list = [g.strip() for g in raw_g.split(",") if g.strip()]
            elif isinstance(raw_g, (list, tuple, set)):
                g_list = [str(g).strip() for g in raw_g if str(g).strip()]
            else:
                g_list = []

            pruned_candidates.append({
                "title": title_val,
                "year": year_val,
                "genres": g_list,
            })

    candidate_block = (
        json.dumps(pruned_candidates, indent=2)
        if pruned_candidates
        else "(no catalog data available - use only well-known, real movies)"
    )
    extra_request = f'\nUser\'s specific request: "{user_message}"' if user_message else ""

    return f"""You are a movie recommendation engine. Given a user's profile and a
pool of candidate movies, select and rank the best matches based on the user's preferences.

User profile:
{json.dumps(profile, indent=2)}

Rules:
1. You MUST select movies from the candidate list below. Do NOT suggest movies outside this list.
2. Prioritize movies whose genres directly match the user's favorite genres. Movies matching favorite genres must be ranked highest with the highest confidence.
3. Do NOT recommend movies that the user has already watched.
4. Set a realistic confidence score (between 0.1 and 1.0) reflecting how well each movie matches the profile.

Candidate movies:
{candidate_block}
{extra_request}

Respond with ONLY a JSON object matching this exact shape, no markdown fences,
no commentary before or after:

{{
  "recommendations": [
    {{
      "title": "string",
      "year": 0000,
      "genres": ["string"],
      "reason": "one sentence on why this matches the user's profile",
      "confidence": 0.0
    }}
  ]
}}

Return up to 8 recommendations."""


def call_llm(prompt: str) -> dict:
    """
    Calls the local model via Ollama's OpenAI-compatible endpoint.
    """
    resp = requests.post(
        f"{MODEL_SERVER_URL}/v1/chat/completions",
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "think": False,
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    raw_text = data["choices"][0]["message"]["content"]
    return _parse_json(raw_text)


def _parse_json(raw_text: str) -> dict:
    """
    Removes unnecessary text commonly appended by the AI model:
    - Spaces
    - ```
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).replace("json", "", 1)
    return json.loads(cleaned)


def generate_recommendations(profile: dict, candidates: list, user_message: str | None = None) -> dict:
    """
    Full pipeline: Prompt -> Call LLM -> Validate (with retries).
    """
    prompt = build_prompt(profile, candidates, user_message)

    last_error = None
    for attempt in range(1, MAX_LLM_RETRIES + 2):
        try:
            parsed = call_llm(prompt)
            validate(instance=parsed, schema=RECOMMENDATION_SCHEMA)
            return parsed
        except (json.JSONDecodeError, ValidationError, KeyError, requests.RequestException) as exc:
            last_error = exc
            logger.warning("LLM attempt %d failed: %s", attempt, exc)

    raise RuntimeError(f"Failed to get valid recommendations after retries: {last_error}")


# ================================================================================================ #
# ========== Routes ============================================================================== #
# ================================================================================================ #
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/recommendations/generate", methods=["POST"])
@require_auth
def generate():
    """
    Synchronous, user-facing endpoint.
    Expects optional: { "message": "optional free text" }
    (candidates in request body is optional; if omitted, fetched internally from movies-service)
    """
    body = request.get_json(silent=True) or {}
    message = body.get("message")

    # Forward Authorization header to internal services
    headers = {}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header

    # Fetch profile from profiles-service using the Bearer token
    try:
        resp = requests.get(
            f"{PROFILES_SERVICE_URL}/profiles/me",
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        profile = resp.json()
    except requests.RequestException as exc:
        logger.error("Failed to fetch user profile: %s", exc)
        return jsonify({"error": "failed to fetch user profile"}), 502

    # If client passed non-empty candidates (e.g. tests or external caller), use them after filtering/pruning;
    # otherwise query movies-service internally
    client_candidates = body.get("candidates")
    if client_candidates and isinstance(client_candidates, list) and len(client_candidates) > 0:
        candidates = filter_and_prune_candidates(client_candidates, profile)[:CANDIDATE_LIMIT]
    else:
        candidates = fetch_candidate_movies(profile, headers)

    try:
        result = generate_recommendations(profile, candidates, message)
    except RuntimeError as exc:
        logger.error("Generation failed: %s", exc)
        return jsonify({"error": "recommendation generation failed"}), 502

    return jsonify({
        "recommendations": result["recommendations"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }), 200


# @app.route("/internal/recommendations/batch", methods=["POST"])
# def generate_batch():
#     """
#     Internal-only endpoint used by the Background Agent service to
#     pre-generate recommendations for many users at once.
#     Expects: { "users": [ { "user_id": "...", "profile": {...} }, ... ] }
#     Not intended to be exposed through the public API gateway.
#     """
#     body = request.get_json(silent=True) or {}
#     users = body.get("users", [])

#     if not users:
#         return jsonify({"error": "users list is required"}), 400

#     results = []
#     for entry in users:
#         user_id = entry.get("user_id")
#         profile = entry.get("profile")
#         if not user_id or not profile:
#             results.append({"user_id": user_id, "error": "missing profile"})
#             continue
#         try:
#             result = generate_recommendations(profile, candidates=[])
#             results.append({
#                 "user_id": user_id,
#                 "recommendations": result["recommendations"],
#                 "generated_at": datetime.now(timezone.utc).isoformat(),
#             })
#         except RuntimeError as exc:
#             logger.error("Batch generation failed for user %s: %s", user_id, exc)
#             results.append({"user_id": user_id, "error": "generation failed"})

#     return jsonify({"results": results}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
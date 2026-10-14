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
import re
import time
import json
import random
import logging
from datetime import datetime, timezone
from functools import wraps
from telemetry import init_metrics, get_llm_duration_histogram

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

# Service Variables
INFERENCE_SERVICE_NAME = os.environ.get("INFERENCE_SERVICE_NAME", "inference-service")
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
DISABLE_INFERENCE_SERVICE_METRICS = os.environ.get("DISABLE_INFERENCE_SERVICE_METRICS", "true").lower() in ("true", "1", "yes")

# Internal Services
PROFILES_SERVICE_URL = os.environ.get("PROFILES_SERVICE_URL", "http://profiles-service:3000")
MOVIES_SERVICE_URL = os.environ.get("MOVIES_SERVICE_URL", "http://movies-service:3001")

# Ollama service
MODEL_SERVER_URL = os.environ.get("MODEL_SERVER_URL")
MODEL_NAME = os.environ.get("MODEL_NAME", "qwen2.5:0.5b")
MAX_LLM_RETRIES = int(os.environ.get("MAX_LLM_RETRIES", 2))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", 500))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", 600))

# Candidate retrieval settings
CANDIDATE_LIMIT = int(os.environ.get("CANDIDATE_LIMIT", 15))

# Security / Keycloak Configuration
KEYCLOAK_JWKS_URL = os.environ.get("KEYCLOAK_JWKS_URL")
KEYCLOAK_ISSUER = os.environ.get("KEYCLOAK_ISSUER")
AUDIENCE = os.environ.get("AUDIENCE")
DISABLE_AUTH = os.environ.get("DISABLE_AUTH", "false").lower() in ("true", "1", "yes")

jwks_client = PyJWKClient(KEYCLOAK_JWKS_URL) if KEYCLOAK_JWKS_URL else None

if not DISABLE_INFERENCE_SERVICE_METRICS:
    init_metrics(INFERENCE_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT)
    llm_duration = get_llm_duration_histogram(INFERENCE_SERVICE_NAME)

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
                "required": ["title", "confidence"],
                "properties": {
                    "title": {"type": "string"},
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
    Filters out watched movies (and favorite movie), and prunes each movie to
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
                t_base = re.sub(r"\s*\(\d{4}\)$", "", t_clean).strip()
                if t_base:
                    watched_titles.add(t_base)

    fav_movie_clean = str(profile.get("favorite_movie") or "").strip().lower()
    if fav_movie_clean:
        watched_titles.add(fav_movie_clean)
        fav_base = re.sub(r"\s*\(\d{4}\)$", "", fav_movie_clean).strip()
        if fav_base:
            watched_titles.add(fav_base)

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
        title_base = re.sub(r"\s*\(\d{4}\)$", "", title_lower).strip()

        # 1. Deduplicate by title
        if title_lower in seen_titles or title_base in seen_titles:
            continue

        # 2. Exclude watched movies (case-insensitive title check)
        if title_lower in watched_titles or title_base in watched_titles:
            continue

        raw_genres = m.get("genres")
        if isinstance(raw_genres, str):
            genre_items = [g.strip() for g in raw_genres.split(",") if g.strip()]
        elif isinstance(raw_genres, (list, tuple, set)):
            genre_items = [str(g).strip() for g in raw_genres if str(g).strip()]
        else:
            genre_items = []

        year = m.get("release_year")
        if year is None:
            year = m.get("year")
        try:
            year = int(year) if year is not None else None
        except (ValueError, TypeError):
            year = None

        synopsis = m.get("synopsis")
        synopsis_clean = str(synopsis).strip() if synopsis is not None else ""

        raw_rating = m.get("rating")
        try:
            rating = float(raw_rating) if raw_rating is not None else None
            if rating is not None:
                rating = round(min(5.0, rating / 2.0 if rating > 5.0 else rating), 1)
        except (ValueError, TypeError):
            rating = None

        seen_titles.add(title_lower)
        if title_base:
            seen_titles.add(title_base)
        item = {
            "title": title_clean,
            "year": year,
            "genres": genre_items,
        }
        if rating is not None:
            item["rating"] = rating
        if synopsis_clean:
            item["synopsis"] = synopsis_clean
        pruned.append(item)

    return pruned


def extract_fav_genres(profile: dict | None) -> set[str]:
    if not profile or not isinstance(profile, dict):
        return set()
    raw = profile.get("favorite_genres") or []
    if isinstance(raw, str):
        return {g.strip().lower() for g in raw.split(",") if g.strip()}
    elif isinstance(raw, (list, tuple, set)):
        return {str(g).strip().lower() for g in raw if str(g).strip()}
    return set()


def get_movie_genre_overlap(movie: dict, fav_genres: set[str]) -> int:
    if not fav_genres or not isinstance(movie, dict):
        return 0
    raw_genres = movie.get("genres") or []
    if isinstance(raw_genres, str):
        m_genres = {g.strip().lower() for g in raw_genres.split(",") if g.strip()}
    elif isinstance(raw_genres, (list, tuple, set)):
        m_genres = {str(g).strip().lower() for g in raw_genres if str(g).strip()}
    else:
        m_genres = set()
    return len(m_genres & fav_genres)


def sample_diverse_candidates(
    candidates: list[dict],
    profile: dict | None = None,
    limit: int = CANDIDATE_LIMIT,
) -> list[dict]:
    """
    Selects candidate movies prioritizing exact genre matches first,
    while randomizing within tiers so recommendations remain fresh and diverse.
    """
    if not candidates or len(candidates) <= limit:
        return list(candidates)

    fav_genres = extract_fav_genres(profile)
    if not fav_genres:
        anchors = candidates[:2]
        pool = candidates[2:]
        needed = limit - len(anchors)
        return anchors + random.sample(pool, min(len(pool), needed))

    # Group candidates by genre overlap count descending
    tier_map: dict[int, list[dict]] = {}
    for c in candidates:
        overlap = get_movie_genre_overlap(c, fav_genres)
        tier_map.setdefault(overlap, []).append(c)

    selected = []
    for overlap in sorted(tier_map.keys(), reverse=True):
        tier = tier_map[overlap]
        needed = limit - len(selected)
        if needed <= 0:
            break
        if len(tier) <= needed:
            selected.extend(tier)
        else:
            # Randomly sample within this tier for variety
            selected.extend(random.sample(tier, needed))

    return selected


def fetch_candidate_movies(
    profile: dict,
    headers: dict | None = None,
) -> list[dict]:
    """
    Queries movies-service for candidates matching user profile preferences,
    filters out watched movies, prunes to minimal fields,
    and samples a diverse pool of candidate movies.
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

    raw_actors = profile.get("favorite_actors") or []
    if isinstance(raw_actors, str):
        actor_list = [a.strip() for a in raw_actors.split(",") if a.strip()]
    elif isinstance(raw_actors, (list, tuple, set)):
        actor_list = [str(a).strip() for a in raw_actors if str(a).strip()]
    else:
        actor_list = []

    params = {"limit": 100}
    if fav_list:
        params["genres"] = ",".join(fav_list)
    if actor_list:
        params["actors"] = ",".join(actor_list)

    # Extract watched titles and favorite movie to pass to movies-service
    # so watched movies are removed directly at the candidate selection level
    watched_titles = []
    for item in (profile.get("watch_history") or []):
        if isinstance(item, dict):
            t = item.get("title") or item.get("name")
        elif isinstance(item, (str, int, float)):
            t = str(item)
        else:
            t = None
        if t is not None:
            t_clean = str(t).strip()
            if t_clean:
                watched_titles.append(t_clean)
                t_base = re.sub(r"\s*\(\d{4}\)$", "", t_clean).strip()
                if t_base:
                    watched_titles.append(t_base)

    fav_movie_clean = str(profile.get("favorite_movie") or "").strip()
    if fav_movie_clean:
        watched_titles.append(fav_movie_clean)
        fav_base = re.sub(r"\s*\(\d{4}\)$", "", fav_movie_clean).strip()
        if fav_base:
            watched_titles.append(fav_base)
        params["favorite_movie"] = fav_movie_clean

    if watched_titles:
        params["watched"] = list(dict.fromkeys(watched_titles))

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

    # Filter out watched movies, prune to essential fields, and sample diverse candidates
    candidates = filter_and_prune_candidates(movies, profile)
    return sample_diverse_candidates(candidates, profile, CANDIDATE_LIMIT)


def build_prompt(profile: dict, candidates: list, user_message: str | None) -> str:
    """
    Generates the prompt (to send to AI model), based on:
    - The user's preferences (favorite movie, favorite genres, favorite actors)
    - Movie candidates (with watched titles and favorite movie already filtered out by movies-service)
    - Optionally, a custom user message

    Watch history is purposefully omitted to keep the LLM's context clean and focused.
    """
    pruned_candidates = (candidates or [])[:CANDIDATE_LIMIT]
    candidate_block = (
        json.dumps(pruned_candidates, separators=(",", ":"))
        if pruned_candidates
        else "(no catalog data available - use only well-known, real movies)"
    )
    fav_movie = str(profile.get("favorite_movie") or "").strip()
    fav_movie_clause = (
        f'\nUser\'s all-time favorite movie: "{fav_movie}". Use this to understand their aesthetic and thematic taste (e.g. emotional depth, drama, tone, or character focus). Recommend movies sharing similar themes or artistic appeal (do NOT match based on literal words in the title).'
        if fav_movie
        else ""
    )

    raw_actors = profile.get("favorite_actors") or []
    if isinstance(raw_actors, str):
        fav_actors_list = [a.strip() for a in raw_actors.split(",") if a.strip()]
    elif isinstance(raw_actors, (list, tuple, set)):
        fav_actors_list = [str(a).strip() for a in raw_actors if str(a).strip()]
    else:
        fav_actors_list = []
    fav_actors_str = ", ".join(fav_actors_list)
    fav_actors_clause = (
        f'\nUser\'s favorite actors: "{fav_actors_str}". Heavily prioritize movies starring these actors when present in the candidates.'
        if fav_actors_str
        else ""
    )

    raw_favs = profile.get("favorite_genres") or []
    if isinstance(raw_favs, str):
        fav_genres = [g.strip() for g in raw_favs.split(",") if g.strip()]
    elif isinstance(raw_favs, (list, tuple, set)):
        fav_genres = [str(g).strip() for g in raw_favs if str(g).strip()]
    else:
        fav_genres = []

    # Clean profile context: only high-signal taste preferences, strictly omitting watch history
    clean_profile = {}
    if fav_movie:
        clean_profile["favorite_movie"] = fav_movie
    if fav_genres:
        clean_profile["favorite_genres"] = fav_genres
    if fav_actors_list:
        clean_profile["favorite_actors"] = fav_actors_list

    fav_genres_str = ", ".join(fav_genres) if fav_genres else ""
    genre_priority_rule = (
        f"2. Heavily prioritize movies whose genres match the user's favorite genres ({fav_genres_str}). Movies matching multiple or all of these genres MUST be ranked higher with higher confidence than movies matching only one or none."
        if fav_genres_str
        else "2. Heavily prioritize movies whose genres and themes best match the user's taste."
    )
    actor_rule = (
        f'3. If a candidate stars one of the user\'s favorite actors ("{fav_actors_str}") and aligns with the favorite genres, rank it at or near the top with high confidence.'
        if fav_actors_str
        else "3. If a candidate aligns closely with the user's favorite movie and genres, rank it at or near the top with high confidence."
    )
    extra_request = f'\nUser\'s specific request: "{user_message}"' if user_message else ""

    return f"""You are a movie recommendation engine. Given a user's preferences and a
pool of candidate movies, select and rank the best matches based on the user's taste.

User preferences:
{json.dumps(clean_profile, separators=(",", ":"))}
{fav_movie_clause}
{fav_actors_clause}

Rules:
1. You MUST select movies from the candidate list below. Do NOT suggest movies outside this list.
{genre_priority_rule}
{actor_rule}
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
      "confidence": 0.0
    }}
  ]
}}

Return 5 recommendations."""


def call_llm(prompt: str) -> dict:
    """
    Calls the local model via Ollama's OpenAI-compatible endpoint.
    """
    resp = requests.post(
        f"{MODEL_SERVER_URL}/v1/chat/completions",
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "movie_recommendations",
                    "strict": True,
                    "schema": RECOMMENDATION_SCHEMA,
                },
            },
            "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.4")),
            "max_tokens": MAX_TOKENS,
            "think": False,
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    raw_text = data["choices"][0]["message"]["content"]
    return parse_json(raw_text)


def repair_truncated_json(text: str) -> str:
    """
    Attempts to close unclosed brackets/braces in a truncated or malformed
    JSON string by tracking delimiter state outside of string literals.
    If truncation happened mid-item inside the recommendations array, rewinds
    to the last complete item object before closing `]}`.
    """
    stack = []
    in_string = False
    escape = False
    last_complete_item_end = None

    for idx, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if in_string:
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch in ("{", "["):
            stack.append(ch)
        elif ch == "}":
            if stack and stack[-1] == "{":
                stack.pop()
                # Just closed an object inside the root object's array: stack is ['{', '[']
                if stack == ["{", "["]:
                    last_complete_item_end = idx
        elif ch == "]":
            if stack and stack[-1] == "[":
                stack.pop()

    # 1. If we ended cleanly at the boundary of the root or array (not mid-item/mid-string),
    #    close any remaining open delimiters directly.
    if not in_string and stack in (["{"], ["{", "["]):
        trimmed = text.rstrip().rstrip(",")
        closing = "".join("}" if opener == "{" else "]" for opener in reversed(stack))
        candidate = trimmed + closing
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # 2. If truncated mid-object or mid-string inside the array, salvage up to the
    #    last complete recommendation object and close with `]}`.
    if last_complete_item_end is not None:
        return text[: last_complete_item_end + 1] + "]}"

    # 3. Fallback: close open string (if any) and all remaining open brackets/braces.
    repaired = text.rstrip()
    if in_string:
        repaired += '"'
    repaired = repaired.rstrip(",")
    closing = "".join("}" if opener == "{" else "]" for opener in reversed(stack))
    return repaired + closing


def parse_json(raw_text: str) -> dict:
    """
    Parses JSON from the LLM response, stripping markdown fences/preambles
    and repairing unclosed brackets if generation was truncated.
    """
    cleaned = raw_text.strip()

    # Strip markdown code fences safely without corrupting payload content
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1 :]
        else:
            cleaned = cleaned.lstrip("`")
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    # Jump to the first '{' in case the model emitted leading commentary
    first_brace = cleaned.find("{")
    if first_brace > 0:
        cleaned = cleaned[first_brace:]

    decoder = json.JSONDecoder()
    try:
        parsed, _ = decoder.raw_decode(cleaned)
        return parsed
    except json.JSONDecodeError:
        repaired = repair_truncated_json(cleaned)
        parsed, _ = decoder.raw_decode(repaired)
        return parsed


def enrich_recommendations(llm_recs: list[dict], candidates: list[dict]) -> list[dict]:
    """
    Populates catalog fields (year, genres, reason=synopsis) directly from the
    candidate pool rather than relying on the LLM to reproduce them.
    """
    candidate_map = {
        str(m["title"]).strip().lower(): m
        for m in (candidates or [])
        if isinstance(m, dict) and m.get("title")
    }

    enriched = []
    seen = set()
    for rec in (llm_recs or []):
        raw_title = str(rec.get("title") or "").strip()
        if not raw_title:
            continue

        key = raw_title.lower()
        cand = candidate_map.get(key)
        # Fallback if the LLM appended "(YYYY)" to the title
        if cand is None and key.endswith(")") and "(" in key:
            stripped_key = key[: key.rfind("(")].strip()
            cand = candidate_map.get(stripped_key)
            if cand is not None:
                key = stripped_key

        if cand is None or key in seen:
            continue

        seen.add(key)
        enriched.append({
            "title": cand["title"],
            "year": cand.get("year"),
            "genres": cand.get("genres") or [],
            "reason": cand.get("synopsis") or "",
            "confidence": rec["confidence"],
            "avg_rating": cand.get("rating"),
            "rating": cand.get("rating"),
        })

    return enriched


def generate_recommendations(profile: dict, candidates: list, user_message: str | None = None) -> dict:
    """
    Full pipeline: Prompt -> Call LLM -> Validate (with retries) -> Enrich with catalog data.
    """
    prompt = build_prompt(profile, candidates, user_message)

    last_error = None
    for attempt in range(1, MAX_LLM_RETRIES + 2):
        try:
            parsed = call_llm(prompt)
            validate(instance=parsed, schema=RECOMMENDATION_SCHEMA)
            return {
                "recommendations": enrich_recommendations(parsed["recommendations"], candidates)
            }
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
        candidates = sample_diverse_candidates(
            filter_and_prune_candidates(client_candidates, profile),
            profile,
            CANDIDATE_LIMIT,
        )
    else:
        candidates = fetch_candidate_movies(profile, headers)

    if not DISABLE_INFERENCE_SERVICE_METRICS:
        start = time.perf_counter()
        status = "success"
    try:
        result = generate_recommendations(profile, candidates, message)
    except RuntimeError as exc:
        if not DISABLE_INFERENCE_SERVICE_METRICS:
            status = "error"
        logger.error("Generation failed: %s", exc)
        return jsonify({"error": "recommendation generation failed"}), 502
    finally:
        if not DISABLE_INFERENCE_SERVICE_METRICS:
            llm_duration.record(
                time.perf_counter() - start,
                {"status": status},
            )

    return jsonify({
        "recommendations": result["recommendations"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }), 200

@app.route("/recommendations/generate/<user_id>", methods=["POST"])
def generate_for_user(user_id):
    """
    Synchronous, user-facing endpoint.
    Expects optional: { "message": "optional free text" }
    (candidates in request body is optional; if omitted, fetched internally from movies-service)
    """
    body = request.get_json(silent=True) or {}
    message = body.get("message")

    # Fetch profile from profiles-service
    try:
        resp = requests.get(f"{PROFILES_SERVICE_URL}/profiles/user/{user_id}", timeout=10)
        resp.raise_for_status()
        profile = resp.json()
    except requests.RequestException as exc:
        logger.error("Failed to fetch user profile: %s", exc)
        return jsonify({"error": "failed to fetch user profile"}), 502

    # If client passed non-empty candidates (e.g. tests or external caller), use them after filtering/pruning;
    # otherwise query movies-service internally
    client_candidates = body.get("candidates")
    if client_candidates and isinstance(client_candidates, list) and len(client_candidates) > 0:
        candidates = sample_diverse_candidates(
            filter_and_prune_candidates(client_candidates, profile),
            profile,
            CANDIDATE_LIMIT,
        )
    else:
        candidates = fetch_candidate_movies(profile)

    if not DISABLE_INFERENCE_SERVICE_METRICS:
        start = time.perf_counter()
        status = "success"
    try:
        result = generate_recommendations(profile, candidates, message)
    except RuntimeError as exc:
        if not DISABLE_INFERENCE_SERVICE_METRICS:
            status = "error"
        logger.error("Generation failed: %s", exc)
        return jsonify({"error": "recommendation generation failed"}), 502
    finally:
        if not DISABLE_INFERENCE_SERVICE_METRICS:
            llm_duration.record(
                time.perf_counter() - start,
                {"status": status},
            )

    return jsonify({
        "recommendations": result["recommendations"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
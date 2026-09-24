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

# Profiles service
PROFILES_SERVICE_URL = os.environ.get("PROFILES_SERVICE_URL")

# Ollama service
MODEL_SERVER_URL = os.environ.get("MODEL_SERVER_URL")
MODEL_NAME = os.environ.get("MODEL_NAME", "llama3.2:1b")
MAX_LLM_RETRIES = int(os.environ.get("MAX_LLM_RETRIES", 2))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", 600))

# Security / Keycloak Configuration
KEYCLOAK_JWKS_URL = os.environ.get("KEYCLOAK_JWKS_URL")
KEYCLOAK_ISSUER = os.environ.get("KEYCLOAK_ISSUER")
AUDIENCE = os.environ.get("AUDIENCE")

if not KEYCLOAK_JWKS_URL:
    raise RuntimeError("CRITICAL: KEYCLOAK_JWKS_URL environment variable is required for authentication.")

jwks_client = PyJWKClient(KEYCLOAK_JWKS_URL)

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
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
def build_prompt(profile: dict, candidates: list, user_message: str | None) -> str:
    """
    Generates the prompt (to send to AI model), based on:
    - The user's profile
    - Movie candidates
    - Optionally, a custom user message
    """
    candidate_block = (
        json.dumps(candidates, indent=2)
        if candidates
        else "(no catalog data available - use only well-known, real movies)"
    )
    extra_request = f'\nUser\'s specific request: "{user_message}"' if user_message else ""

    return f"""You are a movie recommendation engine. Given a user's profile and a
pool of candidate movies, select and rank the best matches.

User profile:
{json.dumps(profile, indent=2)}

Note: Do NOT recommend movies that the user has already watched.

Candidate movies (prefer these; only go outside this list if none fit well):
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

Return between 3 and 8 recommendations."""


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
            "temperature": 0.7,
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
    Expects: { "candidates": [...], "message": "optional free text" }
    """
    body = request.get_json(silent=True) or {}
    candidates = body.get("candidates")
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
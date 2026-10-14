import json
import os
import logging
from functools import wraps

import jwt
from jwt import PyJWKClient
import urllib
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from jsonschema import validate, ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("profiles-service")

app = Flask(__name__)
CORS(app)  # allows requests from your Vite dev server (localhost:5173)

PORT = int(os.environ.get('PORT', 3000))

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Keycloak JWT verification configuration from environment
JWKS_URL = os.environ.get('KEYCLOAK_JWKS_URL')
if not JWKS_URL:
    raise RuntimeError("CRITICAL: KEYCLOAK_JWKS_URL environment variable is required.")
jwk_client = PyJWKClient(JWKS_URL)

KEYCLOAK_ISSUER = os.environ.get('KEYCLOAK_ISSUER')
AUDIENCE = os.environ.get('AUDIENCE')

# Cache agent
CACHE_AGENT_URL = os.environ.get('CACHE_AGENT_URL')


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ")[1]

        try:
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            options = {"verify_aud": bool(AUDIENCE)}

            kwargs_jwt = {
                "jwt": token,
                "key": signing_key.key,
                "algorithms": ["RS256"],
                "options": options,
            }
            if AUDIENCE:
                kwargs_jwt["audience"] = AUDIENCE
            if KEYCLOAK_ISSUER:
                kwargs_jwt["issuer"] = KEYCLOAK_ISSUER

            payload = jwt.decode(**kwargs_jwt)
            request.user_id = payload.get("sub")
            request.user_claims = payload

            if not request.user_id:
                return jsonify({"error": "Unauthorized: Token missing sub claim"}), 401

        except Exception as e:
            logger.warning("JWT Verification Failed: %s", e)
            return jsonify({"error": "Unauthorized or invalid token"}), 401

        return f(*args, **kwargs)

    return decorated


def extract_user_identity(claims: dict):
    if not isinstance(claims, dict):
        return "", ""
    name = (
        claims.get("name")
        or f"{claims.get('given_name', '')} {claims.get('family_name', '')}".strip()
        or claims.get("preferred_username")
        or ""
    )
    email = claims.get("email") or ""
    return name, email


# ================================================================================================ #
# ========== Schemas ============================================================================= #
# ================================================================================================ #
ALLOWED_GENRES = [
    "sci-fi", "thriller", "mystery", "drama", "comedy", "action",
    "horror", "romance", "music", "documentary", "animation",
    "fantasy", "crime", "adventure", "war", "history", "family", "western",
]

PROFILE_UPDATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string", "maxLength": 255},
        "email": {"type": "string", "maxLength": 255},
        "favorite_genres": {
            "type": "array",
            "items": {"type": "string", "enum": ALLOWED_GENRES},
        },
        "favorite_actors": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "watch_history": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title"],
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "rating": {"type": "number", "minimum": 0, "maximum": 5},
                },
            },
        },
        "favorite_movie": {"type": "string", "maxLength": 255},
    },
}


# ================================================================================================ #
# ========== Models ============================================================================== #
# ================================================================================================ #
class Profile(db.Model):
    __tablename__ = "profiles"

    user_id = db.Column(db.String(128), primary_key=True)
    name = db.Column(db.String(255), default="")
    email = db.Column(db.String(255), default="")
    favorite_movie = db.Column(db.String(255), default="")
    favorite_genres = db.Column(db.JSON, default=list)
    favorite_actors = db.Column(db.JSON, default=list)
    watch_history = db.Column(db.JSON, default=list)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name or "",
            "email": self.email or "",
            "favorite_movie": self.favorite_movie or "",
            "favorite_genres": self.favorite_genres or [],
            "favorite_actors": self.favorite_actors or [],
            "watch_history": self.watch_history or [],
        }


# ================================================================================================ #
# ========== Helpers ============================================================================= #
# ================================================================================================ #
def notify_cache_agent(user_id: str):
    """
    Notifies cache agent (best effort)
    """
    url = f"{CACHE_AGENT_URL}/events/{user_id}/profile-updated"
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3):
            return
    except Exception:
        logger.exception("Failed to notify cache agent for user %s", user_id)


# ================================================================================================ #
# ========== Routes ============================================================================== #
# ================================================================================================ #
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/profiles/me", methods=["GET"])
@require_auth
def get_my_profile():
    """
    Returns the logged in user profile.
    Auto-creates profile if missing on first request.
    Populates name and email from Keycloak JWT claims.
    Does not notify cache agent until profile is explicitly saved.
    """
    user_id = request.user_id
    claims = getattr(request, "user_claims", {})
    name, email = extract_user_identity(claims)

    profile = db.session.get(Profile, user_id)
    if not profile:
        profile = Profile(user_id=user_id, name=name, email=email)
        db.session.add(profile)
        db.session.commit()
    else:
        updated = False
        if name and profile.name != name:
            profile.name = name
            updated = True
        if email and profile.email != email:
            profile.email = email
            updated = True
        if updated:
            db.session.commit()

    return jsonify(profile.to_dict()), 200


@app.route("/profiles/me", methods=["PATCH"])
@require_auth
def update_my_profile():
    """
    Updates fields on the logged-in user's profile.
    """
    user_id = request.user_id
    claims = getattr(request, "user_claims", {})
    name, email = extract_user_identity(claims)

    profile = db.session.get(Profile, user_id)
    if not profile:
        return jsonify({"error": "this user doesnt have a profile"}), 404

    body = request.get_json(silent=True) or {}

    if not body:
        return jsonify({"error": "request body is empty"}), 400

    try:
        validate(instance=body, schema=PROFILE_UPDATE_SCHEMA)
    except ValidationError as exc:
        return jsonify({"error": f"invalid profile update: {exc.message}"}), 400

    for field in PROFILE_UPDATE_SCHEMA["properties"]:
        if field in body:
            setattr(profile, field, body[field])

    if name and not profile.name:
        profile.name = name
    if email and not profile.email:
        profile.email = email

    db.session.commit()

    # Notify cache agent (best effort)
    notify_cache_agent(user_id)

    return jsonify(profile.to_dict()), 200


@app.route("/profiles", methods=["GET"])
@app.route("/profiles/", methods=["GET"])
def list_profiles():
    """
    Returns user profiles so members can discover what others are watching.
    Supports optional search query ?q=... and optional ?exclude=<user_id>
    """
    q = request.args.get("q", "").strip().lower()
    exclude = request.args.get("exclude", "").strip()

    profiles = db.session.query(Profile).all()
    if exclude:
        profiles = [p for p in profiles if p.user_id != exclude]

    if q:
        filtered = []
        for p in profiles:
            name = (p.name or "").lower()
            email = (p.email or "").lower()
            fav = (p.favorite_movie or "").lower()
            uid = (p.user_id or "").lower()
            genres_str = " ".join(p.favorite_genres or []).lower()
            actors_str = " ".join(p.favorite_actors or []).lower()
            if q in name or q in email or q in fav or q in uid or q in genres_str or q in actors_str:
                filtered.append(p.to_dict())
        return jsonify({"users": filtered}), 200

    return jsonify({"users": [p.to_dict() for p in profiles]}), 200


@app.route("/profiles/<user_id>", methods=["GET"])
@app.route("/profiles/user/<user_id>", methods=["GET"])
def get_user_profile(user_id):
    """
    Returns the requested user profile (including watch history for member discovery).
    """
    profile = db.session.get(Profile, user_id)
    if not profile:
        return jsonify({"error": "Profile not found!"}), 404

    return jsonify(profile.to_dict()), 200


# ================================================================================================ #
# ========== Main function ======================================================================= #
# ================================================================================================ #
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=PORT, debug=True)
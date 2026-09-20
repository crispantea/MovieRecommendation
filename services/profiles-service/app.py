import os
import jwt
from jwt import PyJWKClient
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from jsonschema import validate, ValidationError

app = Flask(__name__)
CORS(app)  # allows requests from your Vite dev server (localhost:5173)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)

# Keycloak JWT verification configuration from environment
JWKS_URL = os.environ.get('KEYCLOAK_JWKS_URL')
AUDIENCE = os.environ.get('AUDIENCE')
jwk_client = PyJWKClient(JWKS_URL) if JWKS_URL else None


# ================================================================================================ #
# ========== Schemas ============================================================================= #
# ================================================================================================ #
ALLOWED_GENRES = [
    "sci-fi", "thriller", "mystery", "drama", "comedy", "action",
    "horror", "romance", "musical", "documentary", "animation",
    "fantasy", "crime", "adventure", "war", "biography",
]

PROFILE_UPDATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "favorite_genres": {
            "type": "array",
            "items": {"type": "string", "enum": ALLOWED_GENRES},
        },
        "favorite_actors": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "disliked_genres": {
            "type": "array",
            "items": {"type": "string", "enum": ALLOWED_GENRES},
        },
        "mood": {"type": "string", "maxLength": 280},
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
        "min_year": {"type": "integer", "minimum": 1900, "maximum": 2100},
        "visibility": {"type": "string", "enum": ["public", "private"]},
    },
}


# ================================================================================================ #
# ========== Models ============================================================================== #
# ================================================================================================ #
class Profile(db.Model):
    __tablename__ = "profiles"

    user_id = db.Column(db.String(128), primary_key=True)
    favorite_genres = db.Column(db.JSON, default=list)
    favorite_actors = db.Column(db.JSON, default=list)
    disliked_genres = db.Column(db.JSON, default=list)
    mood = db.Column(db.String, default="")
    watch_history = db.Column(db.JSON, default=list)
    min_year = db.Column(db.Integer, nullable=True)
    visibility = db.Column(db.String, default="public")

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "favorite_genres": self.favorite_genres,
            "favorite_actors": self.favorite_actors,
            "disliked_genres": self.disliked_genres,
            "mood": self.mood,
            "watch_history": self.watch_history,
            "min_year": self.min_year,
            "visibility": self.visibility,
        }


# ================================================================================================ #
# ========== Helper ============================================================================== #
# ================================================================================================ #
def _get_user_id():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            if jwk_client:
                signing_key = jwk_client.get_signing_key_from_jwt(token)
                options = {"verify_aud": bool(AUDIENCE)}
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience=AUDIENCE if AUDIENCE else None,
                    options=options
                )
            else:
                payload = jwt.decode(token, options={"verify_signature": False})
            
            return payload.get("sub")
        except Exception as e:
            print(f"JWT Verification Failed: {e}")
            return None

    return None


# ================================================================================================ #
# ========== Routes ============================================================================== #
# ================================================================================================ #
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/profiles/me", methods=["GET"])
def get_my_profile():
    """
    Returns the logged in user profile.
    Auto-creates profile if missing on first request.
    """
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized or invalid token"}), 401

    profile = Profile.query.get(user_id)
    if not profile:
        profile = Profile(user_id=user_id)
        db.session.add(profile)
        db.session.commit()

    return jsonify(profile.to_dict()), 200


@app.route("/profiles/me", methods=["PATCH"])
def update_my_profile():
    """
    Updates fields on the logged-in user's profile.
    Auto-creates profile if missing before patching.
    """
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized or invalid token"}), 401

    profile = Profile.query.get(user_id)
    if not profile:
        profile = Profile(user_id=user_id)
        db.session.add(profile)

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

    db.session.commit()

    return jsonify(profile.to_dict()), 200


# ================================================================================================ #
# ========== Main function ======================================================================= #
# ================================================================================================ #
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=3000, debug=True)
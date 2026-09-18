import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from jsonschema import validate, ValidationError

app = Flask(__name__)
CORS(app)  # allows requests from your Vite dev server (localhost:5173)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)


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
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Profile(db.Model):
    __tablename__ = "profiles"

    user_id = db.Column(db.Integer, primary_key=True)
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
# ========== Routes ============================================================================== #
# ================================================================================================ #
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# TODO: Replace by auth service
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if not user or user.password != password:
        return jsonify({"message": "Invalid email or password"}), 401

    return jsonify({"token": "fake-jwt-token", "user_id": user.id}), 200

# TODO: Replace by auth service
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if user:
        return jsonify({"message": "User already exists"}), 401

    user = User(email=email, password=password)
    db.session.add(user)
    db.session.commit()

    # Create profile
    requests.post(
        "http://localhost:3000/profiles",
        json={
            "user_id": user.id
        }
    )

    return jsonify({"token": "fake-jwt-token", "user_id": user.id}), 200


@app.route("/profiles/me", methods=["GET"])
def get_my_profile():
    """
    Returns the logged in user profile.
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    profile = Profile.query.get(user_id)
    if not profile:
        return jsonify({"error": "profile doesn't exist"}), 409

    return jsonify(profile.to_dict()), 201

@app.route("/profiles/me", methods=["PATCH"])
def update_my_profile():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    profile = Profile.query.get(user_id)
    if not profile:
        return jsonify({"error": "profile not found"}), 404

    body = request.get_json(silent=True) or {}

    if not body:
        return jsonify({"error": "request body is empty"}), 400

    try:
        validate(instance=body, schema=PROFILE_UPDATE_SCHEMA)
    except ValidationError as exc:
        return jsonify({"error": f"invalid profile update: {exc.message}"}), 400

    # Only overwrite fields explicitly present in the request (partial update)
    for field in PROFILE_UPDATE_SCHEMA["properties"]:
        if field in body:
            setattr(profile, field, body[field])

    db.session.commit()

    return jsonify(profile.to_dict()), 200

@app.route("/profiles", methods=["POST"])
def create_profile():
    """
    Called by Auth Service right after a user successfully registers.
    Creates an empty default profile for that user_id.
    """
    body = request.get_json(silent=True) or {}
    user_id = body.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    if Profile.query.get(user_id):
        return jsonify({"error": "profile already exists"}), 409

    profile = Profile(user_id=user_id)
    db.session.add(profile)
    db.session.commit()

    return jsonify(profile.to_dict()), 201


# ================================================================================================ #
# ========== Main function ======================================================================= #
# ================================================================================================ #
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=3000, debug=True)
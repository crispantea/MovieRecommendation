import os
import sys
# Prevent duplicate app module instantiation when seed_db imports app
sys.modules.setdefault("app", sys.modules[__name__])
import logging
from functools import wraps

import jwt
from jwt import PyJWKClient
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import cast, or_, desc, asc
from jsonschema import validate, ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("movies-service")

app = Flask(__name__)

# movies-service is strictly an internal microservice serving inference-service.
# Direct browser access is not permitted; CORS is disabled by default to prevent frontend requests.
if os.environ.get("ENABLE_CORS", "false").lower() in ("true", "1", "yes"):
    try:
        from flask_cors import CORS
        CORS(app)
    except ImportError:
        pass

PORT = int(os.environ.get("PORT", 3001))

# Database configuration
db_url = os.environ.get("DATABASE_URL") or "sqlite:///movies.db"
# Normalize postgres URL if needed (e.g. postgres:// or postgresql:// -> postgresql+psycopg2://)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Keycloak JWT verification configuration from environment
JWKS_URL = os.environ.get("KEYCLOAK_JWKS_URL")
KEYCLOAK_ISSUER = os.environ.get("KEYCLOAK_ISSUER")
AUDIENCE = os.environ.get("AUDIENCE", "movies-api")
DISABLE_AUTH = os.environ.get("DISABLE_AUTH", "false").lower() in ("true", "1", "yes")
USE_TEMPLATE_DB = (
    os.environ.get("USE_TEMPLATE_DB")
    or os.environ.get("USE_TEMPLATE_SEED")
    or "true"
).strip().lower() in ("true", "1", "yes")

jwk_client = PyJWKClient(JWKS_URL) if JWKS_URL else None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Allow disabling auth in test mode or via explicit DISABLE_AUTH env
        if app.config.get("TESTING") or DISABLE_AUTH:
            request.user_id = "test-user"
            return f(*args, **kwargs)

        if not jwk_client:
            logger.warning("Auth is required but KEYCLOAK_JWKS_URL is not set.")
            return jsonify({"error": "Auth service not configured"}), 500

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

            if not request.user_id:
                return jsonify({"error": "Unauthorized: Token missing sub claim"}), 401

        except Exception as e:
            logger.warning("JWT Verification Failed: %s", e)
            return jsonify({"error": "Unauthorized or invalid token"}), 401

        return f(*args, **kwargs)

    return decorated


# ================================================================================================ #
# ========== Schemas ============================================================================= #
# ================================================================================================ #
MOVIE_SCHEMA = {
    "type": "object",
    "required": ["title"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer"},
        "title": {"type": "string", "minLength": 1, "maxLength": 512},
        "director": {"type": ["string", "null"], "maxLength": 255},
        "author": {"type": ["string", "null"], "maxLength": 255},
        "cast": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "genres": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "release_year": {"type": ["integer", "null"], "minimum": 1800, "maximum": 2100},
        "duration_minutes": {"type": ["integer", "null"], "minimum": 0},
        "rating": {"type": ["number", "null"], "minimum": 0, "maximum": 10},
        "vote_count": {"type": ["integer", "null"], "minimum": 0},
        "synopsis": {"type": ["string", "null"]},
        "poster_path": {"type": ["string", "null"], "maxLength": 512},
        "imdb_id": {"type": ["string", "null"], "maxLength": 32},
    },
}

MOVIE_UPDATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string", "minLength": 1, "maxLength": 512},
        "director": {"type": ["string", "null"], "maxLength": 255},
        "author": {"type": ["string", "null"], "maxLength": 255},
        "cast": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "genres": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "release_year": {"type": ["integer", "null"], "minimum": 1800, "maximum": 2100},
        "duration_minutes": {"type": ["integer", "null"], "minimum": 0},
        "rating": {"type": ["number", "null"], "minimum": 0, "maximum": 10},
        "vote_count": {"type": ["integer", "null"], "minimum": 0},
        "synopsis": {"type": ["string", "null"]},
        "poster_path": {"type": ["string", "null"], "maxLength": 512},
        "imdb_id": {"type": ["string", "null"], "maxLength": 32},
    },
}


# ================================================================================================ #
# ========== Models ============================================================================== #
# ================================================================================================ #
class Movie(db.Model):
    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(512), nullable=False, index=True)
    director = db.Column(db.String(255), nullable=True, index=True)
    author = db.Column(db.String(255), nullable=True, index=True)
    cast = db.Column(db.JSON, default=list)
    genres = db.Column(db.JSON, default=list)
    release_year = db.Column(db.Integer, nullable=True, index=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    vote_count = db.Column(db.Integer, nullable=True)
    synopsis = db.Column(db.Text, nullable=True)
    poster_path = db.Column(db.String(512), nullable=True)
    imdb_id = db.Column(db.String(32), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "director": self.director,
            "author": self.author,
            "cast": self.cast or [],
            "genres": self.genres or [],
            "release_year": self.release_year,
            "duration_minutes": self.duration_minutes,
            "rating": self.rating,
            "vote_count": self.vote_count,
            "synopsis": self.synopsis,
            "poster_path": self.poster_path,
            "imdb_id": self.imdb_id,
        }



# ================================================================================================ #
# ========== Routes ============================================================================== #
# ================================================================================================ #
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/movies", methods=["GET"])
def list_movies():
    """
    Query and filter movies catalog.
    Supported filters:
      - director / directed_by: case-insensitive substring
      - author: matches author or director (does not match cast)
      - actor / cast: matches actor in cast list
      - year / release_year: exact release year
      - min_year: minimum release year
      - max_year: maximum release year
      - genre / genres: genre contained in genres list
      - title / q: search title
      - min_rating: minimum rating
      - sort_by: release_year, year, rating, title, id (default: id)
      - sort_dir: asc, desc (default: asc)
      - limit: int (default 50, max 100)
      - offset: int (default 0)
    """
    query = db.session.query(Movie)

    # 1. Director filter
    director_arg = request.args.get("director") or request.args.get("directed_by")
    if director_arg:
        query = query.filter(Movie.director.ilike(f"%{director_arg.strip()}%"))

    # 2. Author filter (matches author or director, strictly excluding cast)
    author_arg = request.args.get("author")
    if author_arg:
        author_term = f"%{author_arg.strip()}%"
        query = query.filter(
            or_(
                Movie.author.ilike(author_term),
                Movie.director.ilike(author_term),
            )
        )

    # 3. Actor / Cast filter
    actor_arg = request.args.get("actor") or request.args.get("cast")
    if actor_arg:
        actor_term = f"%{actor_arg.strip()}%"
        query = query.filter(cast(Movie.cast, db.String).ilike(actor_term))

    # 4. Year filters
    year_arg = request.args.get("year") or request.args.get("release_year")
    if year_arg:
        try:
            query = query.filter(Movie.release_year == int(year_arg))
        except ValueError:
            return jsonify({"error": "Parameter 'year' must be an integer"}), 400

    min_year_arg = request.args.get("min_year")
    if min_year_arg:
        try:
            query = query.filter(Movie.release_year >= int(min_year_arg))
        except ValueError:
            return jsonify({"error": "Parameter 'min_year' must be an integer"}), 400

    max_year_arg = request.args.get("max_year")
    if max_year_arg:
        try:
            query = query.filter(Movie.release_year <= int(max_year_arg))
        except ValueError:
            return jsonify({"error": "Parameter 'max_year' must be an integer"}), 400

    # 5. Genre filter (supports single genre, comma-separated genres, or repeated query params)
    raw_genres = request.args.getlist("genre") + request.args.getlist("genres")
    genre_terms = []
    for g in raw_genres:
        for part in g.split(","):
            part_clean = part.strip()
            if part_clean and part_clean not in genre_terms:
                genre_terms.append(part_clean)
    if genre_terms:
        # Match if movie's genres contain ANY of the requested genre terms
        query = query.filter(
            or_(*(cast(Movie.genres, db.String).ilike(f"%{gt}%") for gt in genre_terms))
        )

    # 6. Title / Text Search
    title_arg = request.args.get("title") or request.args.get("q")
    if title_arg:
        query = query.filter(Movie.title.ilike(f"%{title_arg.strip()}%"))

    # 7. Rating filter
    min_rating_arg = request.args.get("min_rating")
    if min_rating_arg:
        try:
            query = query.filter(Movie.rating >= float(min_rating_arg))
        except ValueError:
            return jsonify({"error": "Parameter 'min_rating' must be a number"}), 400

    # 8. IMDb ID filter
    imdb_id_arg = request.args.get("imdb_id")
    if imdb_id_arg:
        query = query.filter(Movie.imdb_id == imdb_id_arg.strip())

    # Count total matching results
    total = query.count()

    # 9. Sorting
    sort_by = (request.args.get("sort_by") or "id").strip().lower()
    sort_dir = (request.args.get("sort_dir") or request.args.get("order") or "asc").strip().lower()
    descending = sort_dir == "desc"

    sort_columns = {
        "id": Movie.id,
        "title": Movie.title,
        "release_year": Movie.release_year,
        "year": Movie.release_year,
        "rating": Movie.rating,
        "director": Movie.director,
        "vote_count": Movie.vote_count,
        "duration_minutes": Movie.duration_minutes,
    }
    col = sort_columns.get(sort_by, Movie.id)
    if sort_by == "rating" and descending:
        if hasattr(desc(col), "nulls_last"):
            col_expr = desc(col).nulls_last()
        elif hasattr(desc(col), "nullslast"):
            col_expr = desc(col).nullslast()
        else:
            col_expr = desc(col)
        query = query.order_by(col_expr)
    elif sort_by == "rating" and not descending:
        if hasattr(asc(col), "nulls_first"):
            col_expr = asc(col).nulls_first()
        elif hasattr(asc(col), "nullsfirst"):
            col_expr = asc(col).nullsfirst()
        else:
            col_expr = asc(col)
        query = query.order_by(col_expr)
    else:
        query = query.order_by(desc(col) if descending else asc(col))

    # 10. Pagination
    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 100)
    except ValueError:
        limit = 50

    try:
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        offset = 0

    movies = query.offset(offset).limit(limit).all()

    return jsonify({
        "movies": [m.to_dict() for m in movies],
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@app.route("/movies/<int:movie_id>", methods=["GET"])
def get_movie(movie_id):
    """
    Fetch a single movie by ID.
    """
    movie = db.session.get(Movie, movie_id)
    if not movie:
        return jsonify({"error": f"Movie with id {movie_id} not found"}), 404
    return jsonify(movie.to_dict()), 200


@app.route("/movies", methods=["POST"])
@require_auth
def create_movie():
    """
    Add a new movie to the catalog. Requires authentication.
    """
    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({"error": "Request body cannot be empty"}), 400

    try:
        validate(instance=body, schema=MOVIE_SCHEMA)
    except ValidationError as exc:
        return jsonify({"error": f"Invalid movie data: {exc.message}"}), 400

    movie = Movie(
        title=body["title"],
        director=body.get("director"),
        author=body.get("author"),
        cast=body.get("cast", []),
        genres=body.get("genres", []),
        release_year=body.get("release_year"),
        duration_minutes=body.get("duration_minutes"),
        rating=body.get("rating"),
        vote_count=body.get("vote_count"),
        synopsis=body.get("synopsis"),
        poster_path=body.get("poster_path"),
        imdb_id=body.get("imdb_id"),
    )
    if "id" in body:
        movie.id = body["id"]

    try:
        db.session.add(movie)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.warning("Failed to create movie: %s", exc)
        return jsonify({"error": f"Failed to create movie: {str(exc)}"}), 400

    return jsonify({"movie": movie.to_dict()}), 201


@app.route("/movies/<int:movie_id>", methods=["PATCH", "PUT"])
@require_auth
def update_movie(movie_id):
    """
    Update movie fields. Requires authentication.
    """
    movie = db.session.get(Movie, movie_id)
    if not movie:
        return jsonify({"error": f"Movie with id {movie_id} not found"}), 404

    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({"error": "Request body cannot be empty"}), 400

    try:
        validate(instance=body, schema=MOVIE_UPDATE_SCHEMA)
    except ValidationError as exc:
        return jsonify({"error": f"Invalid movie update: {exc.message}"}), 400

    for field in MOVIE_UPDATE_SCHEMA["properties"]:
        if field in body:
            setattr(movie, field, body[field])

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.warning("Failed to update movie: %s", exc)
        return jsonify({"error": f"Failed to update movie: {str(exc)}"}), 400

    return jsonify({"movie": movie.to_dict()}), 200


@app.route("/movies/<int:movie_id>", methods=["DELETE"])
@require_auth
def delete_movie(movie_id):
    """
    Delete a movie from the catalog. Requires authentication.
    """
    movie = db.session.get(Movie, movie_id)
    if not movie:
        return jsonify({"error": f"Movie with id {movie_id} not found"}), 404

    try:
        db.session.delete(movie)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.warning("Failed to delete movie: %s", exc)
        return jsonify({"error": f"Failed to delete movie: {str(exc)}"}), 500

    return jsonify({"message": f"Movie {movie_id} deleted successfully"}), 200


@app.route("/movies/seed", methods=["POST"])
@require_auth
def trigger_seed():
    """
    Seed/reseed the database with initial catalog movies.
    Accepts optional {"clear": true, "template": true/false} in body to reset existing catalog.
    """
    import seed_db
    body = request.get_json(silent=True) or {}
    clear = body.get("clear", False)
    use_template = body.get("template")

    try:
        if use_template is True:
            count = seed_db.seed_from_template(clear_existing=clear)
        elif use_template is False:
            count = seed_db.seed_movies(clear_existing=clear, force_template=False)
        else:
            count = seed_db.seed_movies(clear_existing=clear)

        total = db.session.query(Movie).count()
        return jsonify({
            "message": f"Successfully seeded {count} movies",
            "total_movies": total,
        }), 200
    except Exception as exc:
        logger.exception("Error during manual seed trigger: %s", exc)
        db.session.rollback()
        return jsonify({"error": f"Seed failed: {str(exc)}"}), 500


def auto_seed_if_empty():
    """
    Idempotent catalog seeding on startup.
    Populates database with template or full catalog if empty.
    """
    import seed_db
    return seed_db.auto_seed()


def init_db_with_retry(max_retries=10, delay=2):
    """
    Ensures database tables exist and performs initial seed with connection retry logic.
    Provides resilience against database container startup delays.
    """
    import time
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Initializing database (attempt %d/%d)...", attempt, max_retries)
            db.create_all()
            auto_seed_if_empty()
            logger.info("Database initialized and verified successfully.")
            return True
        except Exception as e:
            logger.warning("Database connection/init failed on attempt %d: %s", attempt, e)
            if attempt == max_retries:
                logger.error("Could not initialize database after %d attempts.", max_retries)
                raise
            time.sleep(delay)


# ================================================================================================ #
# ========== Main Execution ====================================================================== #
# ================================================================================================ #
if __name__ == "__main__":
    with app.app_context():
        init_db_with_retry()
    is_debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    app.run(host="0.0.0.0", port=PORT, debug=is_debug)

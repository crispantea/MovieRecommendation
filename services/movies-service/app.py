import os
import re
import time

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import cast, and_, or_, func, case, select

import seed_db

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 3001))

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///movies.db")
db = SQLAlchemy(app)

# ================================================================================================ #
# ========== Model =============================================================================== #
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
    Returns top movie matches.
    Filters by favorite genres and release year if provided,
    and ranks by actor/mood keyword matches first, then by rating and popularity.
    """
    query = db.session.query(Movie)

    # 1. Filter by genres if requested
    # Note: Using `and_` ensures movies must match ALL requested genres (e.g., both Sci-Fi AND Horror)
    # rather than `or_` which would match movies containing any single genre from the list.
    genres = request.args.get("genres") or request.args.get("genre")
    if genres:
        terms = [g.strip() for g in genres.split(",") if g.strip()]
        if terms:
            query = query.filter(and_(*(cast(Movie.genres, db.String).ilike(f"%{t}%") for t in terms)))

    # 2. Filter by minimum release year if requested
    min_year = request.args.get("min_year")
    if min_year:
        try:
            query = query.filter(Movie.release_year >= int(min_year))
        except ValueError:
            pass

    # 3. Soft relevance score from favorite_actors and mood
    match_conditions = []

    actors = request.args.get("actors")
    if actors:
        for actor in (a.strip() for a in actors.split(",") if a.strip()):
            match_conditions.append(
                or_(
                    cast(Movie.cast, db.String).ilike(f"%{actor}%"),
                    Movie.director.ilike(f"%{actor}%"),
                )
            )

    mood = request.args.get("mood")
    if mood:
        raw_words = [w for w in re.findall(r"[a-z0-9]+", mood.lower()) if len(w) > 2]
        if raw_words:
            # Check each word against PostgreSQL's built-in 'english' dictionary:
            # stopwords ("the", "and", "with", etc.) evaluate to an empty tsquery (""),
            # while meaningful words evaluate to a non-empty tsquery.
            row = db.session.execute(
                select(*(cast(func.plainto_tsquery("english", w), db.String) for w in raw_words))
            ).first()
            for word, tsq in zip(raw_words, row or []):
                if tsq:
                    match_conditions.append(
                        or_(
                            Movie.title.ilike(f"%{word}%"),
                            Movie.synopsis.ilike(f"%{word}%"),
                        )
                    )

    # 4. Weighted quality sort: rating * ln(vote_count + 2)
    weighted_score = Movie.rating * func.log(func.coalesce(Movie.vote_count, 0) + 2)

    movies = []
    if match_conditions:
        match_score = sum(case((cond, 1), else_=0) for cond in match_conditions)
        movies = (
            query.filter(or_(*match_conditions))
            .order_by(match_score.desc(), weighted_score.desc().nulls_last())
            .limit(50)
            .all()
        )

    # 5. Fill remaining slots (or all 50 if no actor/mood matches) by weighted quality
    if len(movies) < 50:
        existing_ids = [m.id for m in movies]
        fallback_query = query
        if existing_ids:
            fallback_query = fallback_query.filter(Movie.id.notin_(existing_ids))
        fallback_movies = (
            fallback_query.order_by(weighted_score.desc().nulls_last())
            .limit(50 - len(movies))
            .all()
        )
        movies.extend(fallback_movies)

    return jsonify({
        "movies": [m.to_dict() for m in movies],
        "total": len(movies)
    }), 200

# ================================================================================================ #
# ========== Database Startup Initialization ===================================================== #
# ================================================================================================ #
def init_db(max_retries=10, delay=2):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Initializing database (attempt {attempt}/{max_retries})...")
            db.create_all()
            seed_db.auto_seed(db, Movie)
            print("Database initialized successfully.")
            return True
        except Exception as exc:
            print(f"Database init failed on attempt {attempt}: {exc}")
            if attempt == max_retries:
                raise
            time.sleep(delay)

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=PORT)

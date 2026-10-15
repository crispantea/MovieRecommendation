import os
import time

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import cast, and_, or_, func, case

import seed_db

app = Flask(__name__)
CORS(app)
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

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/movies", methods=["GET", "POST"])
def list_movies():
    """
    Returns top movie matches.
    Filters by favorite genres and release year if provided,
    removes watched titles from the candidate list,
    and ranks by actor and genre matches, then by rating and popularity.
    """
    base_query = db.session.query(Movie)

    body = request.get_json(silent=True) or {}

    min_year = request.args.get("min_year") or body.get("min_year")
    if min_year:
        try:
            base_query = base_query.filter(Movie.release_year >= int(min_year))
        except ValueError:
            pass

    # Exclude watched movies and favorite movie from candidate pool
    raw_watched = request.args.getlist("watched") or request.args.getlist("exclude") or body.get("watched", [])
    if isinstance(raw_watched, str):
        raw_watched = raw_watched.split(",")

    exclude_list = []
    for item in raw_watched:
        if isinstance(item, str):
            exclude_list.extend([t.strip() for t in item.split(",") if t.strip()])

    fav_movie = request.args.get("favorite_movie") or body.get("favorite_movie")
    if fav_movie:
        exclude_list.append(str(fav_movie).strip())

    if exclude_list:
        watched_set = {w.lower() for w in exclude_list if w}
        base_query = base_query.filter(func.lower(Movie.title).notin_(list(watched_set)))

    # 1. Parse genres (broad matching, never strict exclusion across multiple genres)
    genre_conditions = []
    genres = request.args.get("genres") or request.args.get("genre") or body.get("genres")
    if genres:
        terms = [g.strip() for g in genres.split(",") if g.strip()]
        for t in terms:
            genre_conditions.append(cast(Movie.genres, db.String).ilike(f"%{t}%"))

    # 2. Parse favorite actors (additive matching, direct substring)
    actor_conditions = []
    actors = request.args.get("actors") or body.get("actors")
    if isinstance(actors, list):
        actor_list = [str(a).strip() for a in actors if str(a).strip()]
    elif isinstance(actors, str):
        actor_list = [a.strip() for a in actors.split(",") if a.strip()]
    else:
        actor_list = []

    for actor in actor_list:
        actor_conditions.append(
            or_(
                cast(Movie.cast, db.String).ilike(f"%{actor}%"),
                Movie.director.ilike(f"%{actor}%"),
            )
        )

    # 3. Weighted quality sort: rating * ln(vote_count + 2)
    weighted_score = Movie.rating * func.log(func.coalesce(Movie.vote_count, 0) + 2)

    limit = int(request.args.get("limit") or body.get("limit") or 30)
    limit = max(10, min(limit, 50))

    movies = []
    all_match_conditions = actor_conditions + genre_conditions
    if all_match_conditions:
        # Prioritize exact genre matches (5 pts each) and favorite actor presence (40 pts, outweighs any genre combination)
        score_terms = []
        for cond in actor_conditions:
            score_terms.append(case((cond, 10), else_=0))
        for cond in genre_conditions:
            score_terms.append(case((cond, 5), else_=0))
        # Exact multi-genre intersection bonus: if movie matches ALL favorite genres, give massive boost
        if len(genre_conditions) > 1:
            score_terms.append(case((and_(*genre_conditions), 15), else_=0))
        match_score = sum(score_terms)
        movies = (
            base_query.filter(or_(*all_match_conditions))
            .order_by(match_score.desc(), weighted_score.desc().nulls_last())
            .limit(limit)
            .all()
        )

    # 4. Fill remaining candidate slots by weighted quality
    if len(movies) < limit:
        existing_ids = [m.id for m in movies]
        fallback_query = base_query
        if existing_ids:
            fallback_query = fallback_query.filter(Movie.id.notin_(existing_ids))
        fallback_movies = (
            fallback_query.order_by(weighted_score.desc().nulls_last())
            .limit(limit - len(movies))
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

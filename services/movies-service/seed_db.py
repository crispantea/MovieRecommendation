import os
import gzip
import csv
import json


def auto_seed(db, Movie):
    db.create_all()
    if db.session.query(Movie).first():
        return

    csv_path = os.path.join(os.path.dirname(__file__), "data", "movies.csv.gz")
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found.")
        return

    print("Loading movies from movies.csv.gz...")
    with gzip.open(csv_path, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []
        for r in reader:
            batch.append({
                "id": int(r["id"]),
                "title": r["title"],
                "director": r["director"] or None,
                "author": r["author"] or None,
                "cast": json.loads(r["cast"]) if r["cast"] else [],
                "genres": json.loads(r["genres"]) if r["genres"] else [],
                "release_year": int(r["release_year"]) if r["release_year"] else None,
                "duration_minutes": int(r["duration_minutes"]) if r["duration_minutes"] else None,
                "rating": float(r["rating"]) if r["rating"] else None,
                "vote_count": int(r["vote_count"]) if r["vote_count"] else None,
                "synopsis": r["synopsis"] or None,
                "poster_path": r["poster_path"] or None,
                "imdb_id": r["imdb_id"] or None,
            })
            if len(batch) >= 5000:
                db.session.bulk_insert_mappings(Movie, batch)
                db.session.commit()
                batch = []

        if batch:
            db.session.bulk_insert_mappings(Movie, batch)
            db.session.commit()

    print("Movies loaded successfully.")


if __name__ == "__main__":
    import sys
    from app import app, db, Movie
    with app.app_context():
        if "--clear" in sys.argv:
            print("Clearing existing movie records...")
            db.session.query(Movie).delete()
            db.session.commit()
        auto_seed(db, Movie)

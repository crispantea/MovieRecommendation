import os
import sys
import logging
from typing import Optional

from sqlalchemy import text, insert

# Ensure the directory of this file is at the front of sys.path for robust imports
cur_dir = os.path.dirname(os.path.abspath(__file__))
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)

if "app" in sys.modules and hasattr(sys.modules["app"], "db"):
    app_mod = sys.modules["app"]
    app = getattr(app_mod, "app")
    db = getattr(app_mod, "db")
    Movie = getattr(app_mod, "Movie")
elif "__main__" in sys.modules and hasattr(sys.modules["__main__"], "db"):
    main_mod = sys.modules["__main__"]
    app = getattr(main_mod, "app")
    db = getattr(main_mod, "db")
    Movie = getattr(main_mod, "Movie")
else:
    try:
        from app import app, db, Movie
    except ImportError:
        try:
            from .app import app, db, Movie
        except ImportError:
            sys.path.append(cur_dir)
            from app import app, db, Movie

try:
    from seed_data import INITIAL_MOVIES
except ImportError:
    try:
        from .seed_data import INITIAL_MOVIES
    except ImportError:
        sys.path.append(cur_dir)
        from seed_data import INITIAL_MOVIES

try:
    import pandas as pd
except ImportError:
    pd = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("movies-seeder")

CHUNK_SIZE = 20000


def is_template_mode(force_template: Optional[bool] = None) -> bool:
    """
    Checks whether template database mode should be used.
    Returns True if explicitly requested via parameter or environment variable
    (USE_TEMPLATE_DB, USE_TEMPLATE_SEED). Defaults to True for zero-configuration setup.
    """
    if force_template is not None:
        return bool(force_template)
    raw_val = (
        os.environ.get("USE_TEMPLATE_DB")
        or os.environ.get("USE_TEMPLATE_SEED")
        or "true"
    ).strip().lower()
    return raw_val in ("true", "1", "yes")


def find_csv_file() -> Optional[str]:
    """
    Locates TMDB_all_movies.csv in candidate local directories or downloads via kagglehub.
    Returns path to a non-empty CSV file if found, or None otherwise.
    """
    # 1. Check custom path if explicitly configured
    custom_path = os.environ.get("MOVIES_CSV_PATH")
    if custom_path and os.path.isfile(custom_path) and os.path.getsize(custom_path) > 0:
        logger.info("Found custom CSV dataset at: %s", custom_path)
        return custom_path

    # 2. Check candidate local directories
    candidate_paths = [
        os.path.join(cur_dir, "data", "TMDB_all_movies.csv"),
        os.path.join("/app", "data", "TMDB_all_movies.csv"),
        os.path.abspath("data/TMDB_all_movies.csv"),
    ]

    for path in candidate_paths:
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            logger.info("Found local dataset at: %s", path)
            return path

    # 3. Attempt download via kagglehub if available
    logger.info("Local dataset not found. Attempting download via kagglehub...")
    try:
        import kagglehub

        downloaded_dir = kagglehub.dataset_download("alanvourch/tmdb-movies-daily-updates")
        logger.info("Downloaded dataset to: %s", downloaded_dir)
        for root, _, files in os.walk(downloaded_dir):
            if "TMDB_all_movies.csv" in files:
                csv_path = os.path.join(root, "TMDB_all_movies.csv")
                if os.path.isfile(csv_path) and os.path.getsize(csv_path) > 0:
                    logger.info("Located TMDB_all_movies.csv at: %s", csv_path)
                    return csv_path
    except Exception as exc:
        logger.warning("Could not download dataset via kagglehub: %s", exc)

    logger.info("TMDB_all_movies.csv not available locally or via Kaggle.")
    return None


def parse_genres_fast(val) -> list[str]:
    if val is None:
        return []
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "[]"):
        return []
    items = [g.strip().lower() for g in s.split(",") if g.strip()]
    cleaned = [g for g in items if g not in ("nan", "none", "null")]
    if "science fiction" in cleaned and "sci-fi" not in cleaned:
        cleaned.append("sci-fi")
    return cleaned


def parse_cast_fast(val) -> list[str]:
    if val is None:
        return []
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "[]"):
        return []
    items = [a.strip() for a in s.split(",") if a.strip()]
    cleaned = [a for a in items if a.lower() not in ("nan", "none", "null")]
    return cleaned[:10]


def _create_indexes():
    """
    Creates / verifies database indexes for query performance.
    """
    logger.info("Creating / verifying database indexes...")
    try:
        db.session.execute(
            text("CREATE INDEX IF NOT EXISTS idx_movies_release_year ON movies (release_year);")
        )
        db.session.execute(
            text("CREATE INDEX IF NOT EXISTS idx_movies_director ON movies (director);")
        )
        db.session.execute(
            text("CREATE INDEX IF NOT EXISTS idx_movies_title ON movies (title);")
        )
        db.session.commit()
        logger.info("Indexes verified successfully.")
    except Exception as idx_err:
        logger.warning("Index creation note: %s", idx_err)
        db.session.rollback()


def _sync_sequence():
    """
    Synchronizes PostgreSQL sequence with max id if running on PostgreSQL.
    """
    try:
        bind = getattr(db, "engine", None) or db.session.get_bind()
        if bind and bind.dialect.name == "postgresql":
            db.session.execute(
                text("SELECT setval(pg_get_serial_sequence('movies', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM movies;")
            )
            db.session.commit()
            logger.info("Synchronized PostgreSQL movies id sequence.")
    except Exception as e:
        logger.debug("Sequence synchronization note: %s", e)
        db.session.rollback()


def seed_from_template(clear_existing: bool = False) -> int:
    """
    Seeds database using the curated template seed dataset (seed_data.py).
    Ensures zero manual configuration: works out-of-the-box without Kaggle
    credentials or external CSV files.
    """
    db.create_all()

    if clear_existing:
        logger.info("Clearing existing movie records for template seed...")
        db.session.query(Movie).delete()
        db.session.commit()
        logger.info("Existing records cleared.")

    existing_titles = set()
    if not clear_existing:
        existing = db.session.query(Movie.title, Movie.release_year).all()
        existing_titles = {(r[0].strip().lower(), r[1]) for r in existing if r[0]}
        if existing_titles:
            logger.info("Found %d existing movies in database.", len(existing_titles))

    movies_to_add = []
    for item in INITIAL_MOVIES:
        title = item["title"].strip()
        year = item.get("release_year")
        if (title.lower(), year) in existing_titles:
            continue
        existing_titles.add((title.lower(), year))

        movie = Movie(
            title=title[:512],
            director=str(item["director"]).strip()[:255] if item.get("director") else None,
            author=str(item["author"]).strip()[:255] if item.get("author") else None,
            cast=list(item.get("cast", [])),
            genres=[str(g).strip().lower() for g in item.get("genres", [])],
            release_year=year,
            duration_minutes=item.get("duration_minutes"),
            rating=float(item["rating"]) if item.get("rating") is not None else None,
            vote_count=int(item.get("vote_count", 0)),
            synopsis=str(item["synopsis"]).strip() if item.get("synopsis") else None,
            poster_path=str(item["poster_path"]).strip()[:512] if item.get("poster_path") else None,
            imdb_id=str(item["imdb_id"]).strip()[:32] if item.get("imdb_id") else None,
        )
        movies_to_add.append(movie)

    if movies_to_add:
        db.session.add_all(movies_to_add)
        db.session.commit()
        logger.info("Successfully seeded %d movies from template dataset (seed_data.py).", len(movies_to_add))
    else:
        logger.info("All template movies already present in database. None added.")

    _create_indexes()
    _sync_sequence()
    return len(movies_to_add)


def _seed_from_csv_stdlib(csv_path: str, clear_existing: bool = False) -> int:
    """
    Ingests movies from CSV using Python standard library csv module.
    Works without pandas or external libraries.
    """
    import csv

    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(2147483647)

    if clear_existing:
        logger.info("Clearing existing movie records...")
        db.session.query(Movie).delete()
        db.session.commit()
        logger.info("Existing records cleared.")

    logger.info("Starting ingestion from %s using standard library csv module...", csv_path)
    seen_ids = set()
    total_inserted = 0
    db.create_all()

    if not clear_existing:
        existing_ids = db.session.query(Movie.id).all()
        seen_ids.update(row[0] for row in existing_ids)
        if seen_ids:
            logger.info("Found %d existing movies already in database.", len(seen_ids))

    records = []
    with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_id = (row.get("id") or "").strip()
            if not raw_id.isdigit():
                continue
            m_id = int(raw_id)
            if m_id in seen_ids:
                continue
            seen_ids.add(m_id)

            title = (row.get("title") or "").strip()[:512]
            if not title:
                continue

            release_date = (row.get("release_date") or "").strip()
            year = None
            if len(release_date) >= 4 and release_date[:4].isdigit():
                year = int(release_date[:4])

            runtime_str = (row.get("runtime") or "").strip()
            duration = None
            if runtime_str:
                try:
                    dur_val = float(runtime_str)
                    if dur_val >= 0:
                        duration = int(dur_val)
                except (ValueError, OverflowError):
                    duration = None

            vote_avg_str = (row.get("vote_average") or "").strip()
            try:
                rating = float(vote_avg_str) if vote_avg_str else None
            except (ValueError, OverflowError):
                rating = None

            vote_count_str = (row.get("vote_count") or "").strip()
            try:
                vote_count = int(float(vote_count_str)) if vote_count_str else None
            except (ValueError, OverflowError):
                vote_count = None

            director = (row.get("director") or "").strip()[:255] or None
            writers = (row.get("writers") or "").strip()[:255] or None
            synopsis = (row.get("overview") or "").strip() or None
            poster = (row.get("poster_path") or "").strip()[:512] or None
            imdb = (row.get("imdb_id") or "").strip()[:32] or None

            genres = parse_genres_fast(row.get("genres"))
            cast = parse_cast_fast(row.get("cast"))

            records.append({
                "id": m_id,
                "title": title,
                "director": director,
                "author": writers,
                "cast": cast,
                "genres": genres,
                "release_year": year,
                "duration_minutes": duration,
                "rating": rating,
                "vote_count": vote_count,
                "synopsis": synopsis,
                "poster_path": poster,
                "imdb_id": imdb,
            })

            if len(records) >= CHUNK_SIZE:
                try:
                    db.session.execute(insert(Movie), records)
                except Exception:
                    db.session.bulk_insert_mappings(Movie, records)
                db.session.commit()
                total_inserted += len(records)
                records = []
                logger.info("Inserted %d movies so far...", total_inserted)

    if records:
        try:
            db.session.execute(insert(Movie), records)
        except Exception:
            db.session.bulk_insert_mappings(Movie, records)
        db.session.commit()
        total_inserted += len(records)

    logger.info("Ingestion finished! Total inserted: %d movies.", total_inserted)
    _create_indexes()
    _sync_sequence()
    return total_inserted


def _seed_from_csv(csv_path: str, clear_existing: bool = False) -> int:
    """
    Ingestion function for TMDB_all_movies.csv.
    Uses pandas if available for high-speed chunk processing, otherwise standard library csv.
    """
    if pd is None:
        logger.info("pandas library not found. Falling back to standard library CSV reader.")
        return _seed_from_csv_stdlib(csv_path, clear_existing=clear_existing)

    if clear_existing:
        logger.info("Clearing existing movie records...")
        db.session.query(Movie).delete()
        db.session.commit()
        logger.info("Existing records cleared.")

    logger.info("Starting bulk ingestion from %s with chunksize=%d...", csv_path, CHUNK_SIZE)

    seen_ids = set()
    total_inserted = 0

    # Ensure tables exist
    db.create_all()

    # Pre-populate seen_ids if not clearing
    if not clear_existing:
        existing_ids = db.session.query(Movie.id).all()
        seen_ids.update(row[0] for row in existing_ids)
        if seen_ids:
            logger.info("Found %d existing movies already in database.", len(seen_ids))

    try:
        chunks = pd.read_csv(
            csv_path,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            encoding_errors="replace",
            dtype={"id": str, "release_date": str, "imdb_id": str},
        )

        for chunk_idx, chunk in enumerate(chunks, start=1):
            # 1. Clean and validate numeric ID
            chunk["id_num"] = pd.to_numeric(chunk["id"], errors="coerce")
            chunk = chunk.dropna(subset=["id_num"])
            chunk["id_num"] = chunk["id_num"].astype(int)

            # 2. Filter valid titles
            chunk["title_clean"] = (
                chunk["title"].fillna("").astype(str).str.strip().str[:512]
            )
            chunk = chunk[chunk["title_clean"] != ""]

            # 3. Extract release year from release_date (e.g. '1988-10-21' -> 1988)
            chunk["release_year_clean"] = (
                chunk["release_date"]
                .astype(str)
                .str.extract(r"^(\d{4})")[0]
            )
            chunk["release_year_clean"] = pd.to_numeric(
                chunk["release_year_clean"], errors="coerce"
            )

            # 4. Numeric fields
            chunk["duration_clean"] = pd.to_numeric(chunk["runtime"], errors="coerce")
            chunk["rating_clean"] = pd.to_numeric(chunk["vote_average"], errors="coerce")
            chunk["vote_count_clean"] = pd.to_numeric(chunk["vote_count"], errors="coerce")

            # 5. Lists & text
            chunk["genres_clean"] = chunk["genres"].apply(parse_genres_fast)
            chunk["cast_clean"] = chunk["cast"].apply(parse_cast_fast)

            records = []
            for row in chunk.to_dict(orient="records"):
                m_id = row["id_num"]
                if m_id in seen_ids:
                    continue
                seen_ids.add(m_id)

                director = row.get("director")
                writers = row.get("writers")
                synopsis = row.get("overview")
                poster = row.get("poster_path")
                imdb = row.get("imdb_id")

                year_val = row["release_year_clean"]
                dur_val = row["duration_clean"]
                rate_val = row["rating_clean"]
                votes_val = row["vote_count_clean"]

                records.append({
                    "id": m_id,
                    "title": row["title_clean"],
                    "director": str(director).strip()[:255] if pd.notna(director) and str(director).strip() else None,
                    "author": str(writers).strip()[:255] if pd.notna(writers) and str(writers).strip() else None,
                    "cast": row["cast_clean"],
                    "genres": row["genres_clean"],
                    "release_year": int(year_val) if pd.notna(year_val) else None,
                    "duration_minutes": int(dur_val) if pd.notna(dur_val) else None,
                    "rating": float(rate_val) if pd.notna(rate_val) else None,
                    "vote_count": int(votes_val) if pd.notna(votes_val) else None,
                    "synopsis": str(synopsis).strip() if pd.notna(synopsis) and str(synopsis).strip() else None,
                    "poster_path": str(poster).strip()[:512] if pd.notna(poster) and str(poster).strip() else None,
                    "imdb_id": str(imdb).strip()[:32] if pd.notna(imdb) and str(imdb).strip() else None,
                })

            if records:
                try:
                    db.session.execute(insert(Movie), records)
                except Exception:
                    db.session.bulk_insert_mappings(Movie, records)
                db.session.commit()
                total_inserted += len(records)
                logger.info(
                    "Chunk %d processed. Inserted %d movies (Total so far: %d)...",
                    chunk_idx,
                    len(records),
                    total_inserted,
                )

        logger.info("Bulk ingestion finished! Total inserted: %d movies.", total_inserted)
        _create_indexes()
        _sync_sequence()

    except Exception as exc:
        db.session.rollback()
        logger.exception("Error during movie ingestion: %s", exc)
        raise

    return total_inserted


def seed_movies(clear_existing: bool = False, force_template: Optional[bool] = None) -> int:
    """
    Unified seeding function:
    1. If template mode is requested or configured (USE_TEMPLATE_DB=true),
       seeds from template dataset (seed_data.py).
    2. Otherwise, attempts to find or download TMDB_all_movies.csv.
    3. If CSV dataset is not found, automatically falls back to template seed.
    4. If CSV ingestion fails, gracefully falls back to template seed.
    """
    if is_template_mode(force_template):
        logger.info("Template mode active. Seeding from template dataset (seed_data.py)...")
        return seed_from_template(clear_existing=clear_existing)

    csv_path = find_csv_file()
    if not csv_path:
        logger.info(
            "CSV dataset not found and Kaggle credentials not configured. "
            "Falling back to template dataset (seed_data.py) for zero-configuration startup."
        )
        return seed_from_template(clear_existing=clear_existing)

    try:
        return _seed_from_csv(csv_path, clear_existing=clear_existing)
    except Exception as exc:
        logger.warning(
            "CSV ingestion encountered an error (%s). Falling back to template dataset (seed_data.py) "
            "to ensure zero-configuration operation.",
            exc,
        )
        return seed_from_template(clear_existing=clear_existing)


def auto_seed(force_template: Optional[bool] = None) -> int:
    """
    Idempotent seeding check called at application startup.
    If database already has records, skips seeding.
    Otherwise seeds from template or CSV depending on configuration.
    """
    db.create_all()
    try:
        first_movie = db.session.query(Movie).first()
        if first_movie is not None:
            logger.info("Database already seeded. Skipping auto-seed.")
            return 0
    except Exception as e:
        logger.warning("Could not query existing movies (%s). Rolling back and re-creating...", e)
        db.session.rollback()
        db.create_all()

    logger.info("Database empty. Starting auto-seed pipeline...")
    return seed_movies(clear_existing=False, force_template=force_template)


auto_seed_if_empty = auto_seed


if __name__ == "__main__":
    force_clear = "--clear" in sys.argv or "--force" in sys.argv
    use_template_arg = "--template" in sys.argv
    use_csv_arg = "--csv" in sys.argv or "--full" in sys.argv

    force_template = True if use_template_arg else (False if use_csv_arg else None)

    with app.app_context():
        if force_clear:
            seed_movies(clear_existing=True, force_template=force_template)
        else:
            auto_seed(force_template=force_template)

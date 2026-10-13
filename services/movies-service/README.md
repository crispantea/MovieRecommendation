# Movies Service

Flask API for the movie catalog. For a complete local stack, follow the [repository setup](../../README.md).

## Run Standalone

The service listens on port `3001`, uses SQLite (`movies.db`) by default, and seeds an empty catalog from `data/movies.csv.gz` at startup. To use PostgreSQL, set `DATABASE_URL` before running:

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@localhost:5432/DATABASE'
```

Install and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

FROM python:3.13-slim

# Install curl for healthchecks
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY telemetry.py .
COPY gunicorn.conf.py .

# Use gunicorn in place of Flask's dev server for anything beyond local testing
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
# ref: https://hub.docker.com/_/python
FROM python:3.13-slim

# Install curl for healthchecks
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# IMPORTANT: When building this image, the context should point to the backend application directory
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 3001

CMD ["python", "app.py"]

# Cache Agent

Flask service that stores generated recommendations in Redis, refreshes them after profile updates, and serves cached results. For a complete local stack, follow the [repository setup](../../README.md).

## Run Standalone

Requires Redis, the inference service, and Keycloak. Set these values for your environment:

```bash
export PORT=3002
export REDIS_URL=redis://localhost:6379/0
export INFERENCE_URL=http://localhost:8000
export KEYCLOAK_JWKS_URL=http://localhost:8080/realms/agi-project/protocol/openid-connect/certs
export KEYCLOAK_ISSUER=http://localhost:8080/realms/agi-project
export AUDIENCE=cache-api
```

Install and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
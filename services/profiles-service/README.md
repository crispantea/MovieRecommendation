# Profiles Service

Flask API for user profiles and watch history. For a complete local stack, follow the [repository setup](../../README.md).

## Run Standalone

Requires a reachable PostgreSQL database and Keycloak realm. Set these values for your environment:

```bash
export PORT=3000
export DATABASE_URL='postgresql://USER:PASSWORD@localhost:5432/DATABASE'
export KEYCLOAK_JWKS_URL=http://localhost:8080/realms/agi-project/protocol/openid-connect/certs
export KEYCLOAK_ISSUER=http://localhost:8080/realms/agi-project
export AUDIENCE=profiles-api
```

Then install and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

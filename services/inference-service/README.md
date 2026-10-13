# Inference Service

Flask API that generates recommendations using Ollama. For a complete local stack, follow the [repository setup](../../README.md).

## Run Standalone

Requires running profiles and movies APIs, Keycloak, and Ollama with the configured model available. Set these values for your environment:

```bash
export PORT=8000
export PROFILES_SERVICE_URL=http://localhost:3000
export MOVIES_SERVICE_URL=http://localhost:3001
export MODEL_SERVER_URL=http://localhost:11434
export MODEL_NAME=qwen2.5:0.5b
export KEYCLOAK_JWKS_URL=http://localhost:8080/realms/agi-project/protocol/openid-connect/certs
export KEYCLOAK_ISSUER=http://localhost:8080/realms/agi-project
export AUDIENCE=inference-api
```

Install the model with `ollama pull qwen2.5:0.5b`, then install and run the service:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

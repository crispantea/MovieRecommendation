# Frontend

React/Vite application for authentication, profiles, and movie recommendations.

## Local Development

Set these values in `.env`. Vite loads this file automatically:

```dotenv
VITE_PROFILES_SERVICE_URL=http://localhost:3000
VITE_INFERENCE_SERVICE_URL=http://localhost:8000
VITE_KEYCLOAK_URL=http://localhost:8080
VITE_KEYCLOAK_APP_REALM=agi-project
VITE_KEYCLOAK_APP_CLIENT_ID=agi-web
```

The services must already be running; see [repository setup](../../README.md) for the complete stack setup.

```bash
cp .env.example .env
npm ci
npm run dev
```
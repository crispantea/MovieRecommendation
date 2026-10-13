# AGI Project

A movie recommendation application built from microservices. Users sign in with Keycloak, manage profiles and watch history, and receive recommendations ranked by a locally hosted language model.

## Components

- **Frontend:** React application for sign-in, profiles, and recommendations.
- **Keycloak:** OpenID Connect authentication, backed by PostgreSQL.
- **Profiles service:** Flask API and PostgreSQL database for user profiles and watch history.
- **Movies service:** Flask API and PostgreSQL database for the movie catalog.
- **Inference service:** Flask API that selects and ranks movies using Ollama.
- **Cache agent:** Redis-backed service for caching recommendation requests.
- **Kubernetes deployment:** KGateway handles routing; OpenTelemetry, Grafana, and Mimir provide monitoring.

The services can run locally with Docker Compose or be deployed to Kubernetes with Kind or GCP. Local Compose is the quickest way to run the complete application.

## Local Setup

### Requirements

Install Docker with the Compose plugin, `just`, Terraform, OpenSSL, `envsubst` (from `gettext`), and `jq`. Docker must be running. The first start needs internet access to download container images and the Ollama model.

### Configure and start

From the repository root, review `.env` and `.env.local` for ports and application defaults. The default model is `qwen2.5:0.5b`. Do not commit generated credentials in `.env.secrets`.

Run:

```bash
ENV=local just init
ENV=local just build
ENV=local just local-up
```

`init` generates local passwords in `.env.secrets` and prepares the Keycloak realm configuration. `build` builds the application images and downloads the Ollama image. `local-up` configures Keycloak and starts the services and databases; the first startup may take several minutes while the model is downloaded.

Open the frontend at <http://localhost:5173>. Keycloak is available at <http://localhost:8080>; its administrator password is in `.env.secrets`.

To stop the stack, run `ENV=local just local-clean`. This removes containers and database volumes, so local database data will be lost. `ENV=local just local-destroy` also removes generated secrets.

## Kubernetes Setup

The Kubernetes deployment requires `kubectl`, Helm, and either Kind or a configured GCP project. Initialize secrets before building.

For a local Kind cluster:

```bash
ENV=kind just init
ENV=kind just build
ENV=kind just kind-up
```

For GCP, provide a service-account key at [`infra/environments/dev/gcp/credentials.json`](infra/environments/dev/gcp/credentials.json) and set `GCP_PROJECT_ID` in [`infra/environments/dev/gcp/terraform.tfvars`](infra/environments/dev/gcp/terraform.tfvars). Then initialize and deploy:

```bash
ENV=cloud just init
DOCKER_DEFAULT_PLATFORM=linux/amd64 ENV=cloud just build
ENV=cloud just mgmt-up
ENV=cloud just cloud-infra-init
ENV=cloud just cloud-up
```

The GCP commands provision billable resources. After deployment, the application is available at the master node's external IP on port `30080`. See the `justfile` for cleanup targets and advanced deployment commands.

---

## Troubleshooting

### Common Browser Issue: Insecure `IP:PORT` Access

Browsers block Web Crypto API (required by Keycloak PKCE) on plain HTTP `IP:PORT` origins. In Chrome:
1. Open `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
2. Enable **Insecure origins treated as secure** and add `http://<MASTER_EXTERNAL_IP>:30080`
3. Relaunch Chrome.
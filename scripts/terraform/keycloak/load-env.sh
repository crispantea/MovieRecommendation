#!/usr/bin/env bash
set -euo pipefail

# Validate envrionment variables
REQUIRED_ENV_VARS=(
  "SECRETS_FILE"

  "KEYCLOAK_HOST_PORT"
  "FRONTEND_HOST_PORT"
  
  "KEYCLOAK_TERRAFORM_CLIENT_ID"
  "KEYCLOAK_TERRAFORM_REALM"
  "PROFILES_AUDIENCE"
  "INFERENCE_AUDIENCE"
)

for var in "${REQUIRED_ENV_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "Error: Environment variable '$var' is not set." >&2
    exit 1
  fi
done

# Load and validate secrets
if [ ! -f "./$SECRETS_FILE" ]; then
  echo "Error: Secrets file './$SECRETS_FILE' not found (run: just init)." >&2
  exit 1
fi

. "./$SECRETS_FILE"

if [ -z "${KEYCLOAK_TERRAFORM_SECRET:-}" ]; then
  echo "Error: KEYCLOAK_TERRAFORM_SECRET is not set in $SECRETS_FILE (run: just init)." >&2
  exit 1
fi

# Export terraform input variables
export TF_VAR_keycloak_url="http://localhost:${KEYCLOAK_HOST_PORT}"
export TF_VAR_frontend_url="http://localhost:${FRONTEND_HOST_PORT}"
export TF_VAR_keycloak_realm="${KEYCLOAK_TERRAFORM_REALM}"
export TF_VAR_keycloak_client_id="${KEYCLOAK_TERRAFORM_CLIENT_ID}"
export TF_VAR_keycloak_client_secret="${KEYCLOAK_TERRAFORM_SECRET}"
export TF_VAR_audiences="[\"${PROFILES_AUDIENCE}\",\"${INFERENCE_AUDIENCE}\"]"

echo "Terraform keycloak environment variables configured successfully."
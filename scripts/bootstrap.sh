#!/usr/bin/env bash
set -euo pipefail

# Required environment variables
REQUIRED_BOOTSTRAP_VARS=(
  "SECRETS_FILE"
  "SERVICES_DIR"
)

for v in "${REQUIRED_BOOTSTRAP_VARS[@]}"; do
  if [ -z "${!v:-}" ]; then 
    echo "Error: Variable $v is not set." >&2
    exit 1
  fi
done

# Ensure the secrets file exists with restrictive permissions (chmod 600)
(umask 077; touch "$SECRETS_FILE")

# Secrets array to generate if missing
SECRETS=(
  "KEYCLOAK_TERRAFORM_SECRET"
  "KEYCLOAK_ADMIN_PASSWORD"
  "AUTH_DB_PASSWORD"
  "PROFILES_DB_PASSWORD"
  "MOVIES_DB_PASSWORD"
)

for key in "${SECRETS[@]}"; do
  if ! grep -q "^${key}=" "$SECRETS_FILE"; then
    echo "${key}=$(openssl rand -hex 24)" >> "$SECRETS_FILE"
  fi
done

# Load generated secrets
. "./$SECRETS_FILE"

# Feed realm export template with generated secret if available
if [ -f "$SERVICES_DIR/authorization/import/realm-export.json.template" ]; then
  sed "s|\${KEYCLOAK_TERRAFORM_SECRET}|$KEYCLOAK_TERRAFORM_SECRET|g" \
    "$SERVICES_DIR/authorization/import/realm-export.json.template" > \
    "$SERVICES_DIR/authorization/import/realm-export.json"
fi

echo "Bootstrap complete ($SECRETS_FILE updated and realm template rendered)"
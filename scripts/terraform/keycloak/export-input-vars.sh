#!/usr/bin/env bash
set -euo pipefail

# Append port ONLY if it is non-standard (not 80, 443, or empty)
PORT_SUFFIX=""
if [ -n "${FRONTEND_HOST_PORT:-}" ] && [ "${FRONTEND_HOST_PORT}" != "80" ] && [ "${FRONTEND_HOST_PORT}" != "443" ]; then
  PORT_SUFFIX=":${FRONTEND_HOST_PORT}"
fi

export TF_VAR_keycloak_url="http://${KEYCLOAK_DOMAIN}:${KEYCLOAK_HOST_PORT}${KEYCLOAK_PATH:-}"
export TF_VAR_frontend_url="http://${FRONTEND_DOMAIN}${PORT_SUFFIX}"

export TF_VAR_keycloak_realm="${KEYCLOAK_TERRAFORM_REALM}"
export TF_VAR_keycloak_client_id="${KEYCLOAK_TERRAFORM_CLIENT_ID}"
export TF_VAR_keycloak_client_secret="${KEYCLOAK_TERRAFORM_SECRET}"
export TF_VAR_audiences="[\"${PROFILES_AUDIENCE}\",\"${INFERENCE_AUDIENCE}\",\"${MOVIES_AUDIENCE}\",\"${CACHE_AUDIENCE}\"]"
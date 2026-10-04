#!/usr/bin/env bash
set -euo pipefail

export TF_VAR_keycloak_url="http://${KEYCLOAK_DOMAIN}:${KEYCLOAK_HOST_PORT}${KEYCLOAK_PATH:-}"
export TF_VAR_frontend_url="http://${FRONTEND_DOMAIN}:${FRONTEND_HOST_PORT}${FRONTEND_PATH:-}"

export TF_VAR_keycloak_realm="${KEYCLOAK_TERRAFORM_REALM}"
export TF_VAR_keycloak_client_id="${KEYCLOAK_TERRAFORM_CLIENT_ID}"
export TF_VAR_keycloak_client_secret="${KEYCLOAK_TERRAFORM_SECRET}"
export TF_VAR_audiences="[\"${PROFILES_AUDIENCE}\",\"${INFERENCE_AUDIENCE}\",\"${MOVIES_AUDIENCE}\"]"
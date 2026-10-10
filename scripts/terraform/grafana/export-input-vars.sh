#!/usr/bin/env bash
set -euo pipefail

export TF_VAR_grafana_url="http://${APP_DOMAIN}:${APP_HOST_PORT}${GRAFANA_PATH}"
export TF_VAR_grafana_auth="${GRAFANA_ADMIN_USER}:${GRAFANA_ADMIN_PASSWORD}"

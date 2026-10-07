#!/bin/sh
set -eu

cat <<EOF > /usr/share/nginx/html/config.js
window.__ENV__ = {
  KEYCLOAK_URL: "${KEYCLOAK_URL:-}",
  KEYCLOAK_APP_REALM: "${KEYCLOAK_APP_REALM:-}",
  KEYCLOAK_APP_CLIENT_ID: "${KEYCLOAK_APP_CLIENT_ID:-}",
  PROFILES_SERVICE_URL: "http://${APP_DOMAIN}:${APP_PORT}/profiles",
  INFERENCE_SERVICE_URL: "http://${APP_DOMAIN}:${APP_PORT}/inference"
};
EOF

cat <<EOF > /etc/nginx/conf.d/default.conf
server {
  listen ${PORT};
  root /usr/share/nginx/html;
  index index.html;

  # Disable browser caching specifically for config.js so updates apply immediately
  location = /config.js {
    add_header Cache-Control "no-store, no-cache, must-revalidate";
  }

  location /inference/ {
    proxy_pass ${INFERENCE_SERVICE_INTERNAL_URL}/;
    proxy_set_header Host \$proxy_host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }

  location /profiles/ {
    proxy_pass ${PROFILES_SERVICE_INTERNAL_URL}/;
    proxy_set_header Host \$proxy_host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }

  # SPA Routing fallback
  location / {
    try_files \$uri \$uri/ /index.html;
  }
}
EOF
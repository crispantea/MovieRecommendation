#!/bin/sh
set -eu

cat <<EOF > /usr/share/nginx/html/config.js
window.__ENV__ = {
  KEYCLOAK_URL: "${KEYCLOAK_URL:-}",
  KEYCLOAK_APP_REALM: "${KEYCLOAK_APP_REALM:-}",
  KEYCLOAK_APP_CLIENT_ID: "${KEYCLOAK_APP_CLIENT_ID:-}",
  PROFILES_SERVICE_URL: "${PROFILES_SERVICE_URL:-}",
  INFERENCE_SERVICE_URL: "${INFERENCE_SERVICE_URL:-}",
  CACHE_AGENT_URL: "${CACHE_AGENT_URL:-}"
};
EOF

INFERENCE_BLOCK=""
if [ -n "${INFERENCE_SERVICE_INTERNAL_URL:-}" ]; then
  INFERENCE_BLOCK=$(cat <<EOF

  location /inference/ {
    proxy_pass ${INFERENCE_SERVICE_INTERNAL_URL}/;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    proxy_set_header Host \$proxy_host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
EOF
)
fi

PROFILES_BLOCK=""
if [ -n "${PROFILES_SERVICE_INTERNAL_URL:-}" ]; then
  PROFILES_BLOCK=$(cat <<EOF

  location /profiles/ {
    proxy_pass ${PROFILES_SERVICE_INTERNAL_URL}/;
    proxy_set_header Host \$proxy_host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
EOF
)
fi

CACHE_BLOCK=""
if [ -n "${CACHE_AGENT_INTERNAL_URL:-}" ]; then
  CACHE_BLOCK=$(cat <<EOF

  location /cache/ {
    proxy_pass ${CACHE_AGENT_INTERNAL_URL}/;
    proxy_set_header Host \$proxy_host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
EOF
)
fi

cat <<EOF > /etc/nginx/conf.d/default.conf
server {
  listen ${PORT:-80};
  root /usr/share/nginx/html;
  index index.html;

  # Disable browser caching specifically for config.js so updates apply immediately
  location = /config.js {
    add_header Cache-Control "no-store, no-cache, must-revalidate";
  }
${INFERENCE_BLOCK}
${PROFILES_BLOCK}
${CACHE_BLOCK}

  # SPA Routing fallback
  location / {
    try_files \$uri \$uri/ /index.html;
  }
}
EOF
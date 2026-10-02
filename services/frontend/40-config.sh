#!/bin/sh

cat > /usr/share/nginx/html/config.js <<EOF
window.__ENV__ = {
  KEYCLOAK_URL: "${KEYCLOAK_URL}",
  KEYCLOAK_APP_REALM: "${KEYCLOAK_APP_REALM}",
  KEYCLOAK_APP_CLIENT_ID: "${KEYCLOAK_APP_CLIENT_ID}",
  PROFILES_SERVICE_URL: "${PROFILES_SERVICE_URL}",
  INFERENCE_SERVICE_URL: "${INFERENCE_SERVICE_URL}"
};
EOF

cat > /etc/nginx/conf.d/default.conf <<EOF
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;

  location = /config.js {
    add_header Cache-Control "no-store";
  }

  location /api/inference/ {
    proxy_pass ${INFERENCE_SERVICE_URL}/;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }

  location = /api/profiles {
    proxy_pass ${PROFILES_SERVICE_URL}/profiles;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }

  location /api/profiles/ {
    proxy_pass ${PROFILES_SERVICE_URL}/profiles/;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }

  location / {
    try_files \$uri /index.html;
  }
}
EOF
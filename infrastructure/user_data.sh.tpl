#!/bin/bash
set -euo pipefail
exec > /var/log/assistente-init.log 2>&1

echo "==> Installing Docker..."
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

echo "==> Creating app directory..."
mkdir -p /opt/assistente/Downloads
touch /opt/assistente/assistente.db
cd /opt/assistente

echo "==> Writing docker-compose.yml..."
cat > docker-compose.yml << 'COMPOSE_EOF'
${compose_contents}
COMPOSE_EOF

echo "==> Writing compose override (port 80 + Spaces storage)..."
cat > docker-compose.override.yml << 'OVERRIDE_EOF'
services:
  frontend:
    ports:
      - "80:3000"
  api:
    environment:
      STORAGE_ENDPOINT_URL: ${spaces_endpoint}
      STORAGE_ACCESS_KEY_ID: ${spaces_access_key}
      STORAGE_SECRET_ACCESS_KEY: ${spaces_secret_key}
      STORAGE_BUCKET_NAME: ${spaces_bucket_name}
      STORAGE_PUBLIC_URL: ${spaces_public_url}
      STORAGE_REGION: ${spaces_region}
OVERRIDE_EOF

echo "==> Writing .env..."
cat > .env << 'ENV_EOF'
${env_contents}
ENV_EOF
chmod 600 .env

echo "==> Logging in to GHCR..."
echo "${github_token}" | docker login ghcr.io -u "${github_user}" --password-stdin

echo "==> Pulling images..."
docker compose -f docker-compose.yml -f docker-compose.override.yml pull

echo "==> Starting app..."
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

echo "==> Done. App is running on port 80."
docker compose -f docker-compose.yml -f docker-compose.override.yml ps

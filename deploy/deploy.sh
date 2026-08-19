#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker-compose.release.yml}"
BASE_URL="${BASE_URL:-https://www.jingsaidanao.com}"

cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Install Docker Engine first."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is not available. Install docker-compose-plugin first."
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing env file: $ENV_FILE"
  echo "Create it from .env.production.example and fill production values."
  exit 1
fi

if [ ! -f "$ROOT_DIR/certs/fullchain.pem" ] || [ ! -f "$ROOT_DIR/certs/privkey.pem" ]; then
  echo "Missing TLS certificate files:"
  echo "  $ROOT_DIR/certs/fullchain.pem"
  echo "  $ROOT_DIR/certs/privkey.pem"
  exit 1
fi

echo "Rendering LiveKit config..."
"$ROOT_DIR/livekit/render-livekit-config.sh" "$ENV_FILE" "$ROOT_DIR/livekit/livekit.prod.yaml" "$ROOT_DIR/livekit/livekit.rendered.yaml"

echo "Checking compose config..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config >/dev/null

echo "Building images..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build --parallel

echo "Starting services..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d

echo "Current containers:"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo "Health check:"
for i in 1 2 3 4 5 6; do
  if curl -sk "$BASE_URL/api/auth/check" >/dev/null 2>&1; then
    echo "Backend is reachable: $BASE_URL/api/auth/check"
    exit 0
  fi
  echo "Waiting for backend... ($i/6)"
  sleep 10
done

echo "Services started, but backend health check did not pass yet. Check logs with:"
echo "docker compose --env-file .env.production -f docker-compose.release.yml logs -f backend nginx"

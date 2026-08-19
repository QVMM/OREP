#!/usr/bin/env bash
set -euo pipefail
# Usage (from Mac):
#   bash deploy/partial-update-training-unlock.sh
# Requires: ~/.ssh/orep_codex_deploy and reachable root@39.96.213.213

ROOT="$(cd "$(dirname "$0")" && pwd)"
HOST="${OREP_DEPLOY_HOST:-root@39.96.213.213}"
KEY="${OREP_DEPLOY_KEY:-$HOME/.ssh/orep_codex_deploy}"
REMOTE_DIR="${OREP_REMOTE_DIR:-/opt/orep/deploy}"

echo "[1/4] Sync backend jar + user/teacher frontend dist"
rsync -avz -e "ssh -i $KEY" \
  "$ROOT/backend/orep-backend-1.0.0.jar" \
  "$HOST:$REMOTE_DIR/backend/"
rsync -avz -e "ssh -i $KEY" \
  "$ROOT/frontend/user/dist/" \
  "$HOST:$REMOTE_DIR/frontend/user/dist/"
rsync -avz -e "ssh -i $KEY" \
  "$ROOT/frontend/teacher/dist/" \
  "$HOST:$REMOTE_DIR/frontend/teacher/dist/"

echo "[2/4] Rebuild and recreate only affected services"
ssh -i "$KEY" "$HOST" "cd $REMOTE_DIR && docker compose --env-file .env.production -f docker-compose.release.yml build backend frontend-user frontend-teacher && docker compose --env-file .env.production -f docker-compose.release.yml up -d --no-deps backend frontend-user frontend-teacher"

echo "[3/4] Health check"
ssh -i "$KEY" "$HOST" "cd $REMOTE_DIR && docker compose --env-file .env.production -f docker-compose.release.yml ps backend frontend-user frontend-teacher"

echo "[4/4] Done. Verify: https://www.qvm-onestar.cn/project-team and teacher camp plan unlock."

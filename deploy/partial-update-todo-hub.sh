#!/usr/bin/env bash
set -euo pipefail
# Usage (from Mac, after local build):
#   bash deploy/partial-update-todo-hub.sh
# Requires: ~/.ssh/orep_codex_deploy and reachable root@39.96.213.213
#
# Local prep (if not already done):
#   cd backend && mvn -Dmaven.test.skip=true package
#   cp target/orep-backend-1.0.0.jar ../deploy/backend/
#   cd ../frontend/user && npm run build
#   rsync -a --delete dist/ ../../deploy/frontend/user/dist/

ROOT="$(cd "$(dirname "$0")" && pwd)"
HOST="${OREP_DEPLOY_HOST:-root@39.96.213.213}"
KEY="${OREP_DEPLOY_KEY:-$HOME/.ssh/orep_codex_deploy}"
REMOTE_DIR="${OREP_REMOTE_DIR:-/opt/orep/deploy}"

echo "[1/4] Sync backend jar + user frontend dist + SQL"
rsync -avz -e "ssh -i $KEY -o ServerAliveInterval=15" \
  "$ROOT/backend/orep-backend-1.0.0.jar" \
  "$HOST:$REMOTE_DIR/backend/"
rsync -avz -e "ssh -i $KEY -o ServerAliveInterval=15" \
  "$ROOT/frontend/user/dist/" \
  "$HOST:$REMOTE_DIR/frontend/user/dist/"
rsync -avz -e "ssh -i $KEY -o ServerAliveInterval=15" \
  "$ROOT/sql/migrations/V107__daily_report.sql" \
  "$HOST:$REMOTE_DIR/sql/migrations/"

echo "[2/4] Rebuild and recreate backend + frontend-user"
ssh -i "$KEY" -o ServerAliveInterval=15 "$HOST" \
  "cd $REMOTE_DIR && docker compose --env-file .env.production -f docker-compose.release.yml build backend frontend-user && docker compose --env-file .env.production -f docker-compose.release.yml up -d --no-deps backend frontend-user"

echo "[3/4] Ensure daily_report table (idempotent)"
ssh -i "$KEY" -o ServerAliveInterval=15 "$HOST" \
  "cd $REMOTE_DIR && set -a && . ./.env.production && set +a && docker compose --env-file .env.production -f docker-compose.release.yml exec -T mysql sh -c \"mysql -uroot -p\\\"\\\$MYSQL_ROOT_PASSWORD\\\" \\\"\\\$MYSQL_DATABASE\\\"\" < sql/migrations/V107__daily_report.sql"

echo "[4/4] Health"
ssh -i "$KEY" -o ServerAliveInterval=15 "$HOST" \
  "cd $REMOTE_DIR && docker compose --env-file .env.production -f docker-compose.release.yml ps backend frontend-user"
curl -sk https://www.qvm-onestar.cn/api/auth/check | head -c 200; echo
echo "Done. Verify: open 待办中心 → 今日必做 → 填写日报"

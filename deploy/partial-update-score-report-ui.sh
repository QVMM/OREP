#!/usr/bin/env bash
# Partial production update: AI score report UI + scoring AI service
# Usage (from Mac, project root or deploy/):
#   bash deploy/partial-update-score-report-ui.sh
#
# Requires:
#   - ~/.ssh/orep_codex_deploy
#   - reachable root@39.96.213.213 (or override OREP_DEPLOY_HOST / OREP_DEPLOY_KEY)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$ROOT/.." && pwd)"
HOST="${OREP_DEPLOY_HOST:-root@39.96.213.213}"
KEY="${OREP_DEPLOY_KEY:-$HOME/.ssh/orep_codex_deploy}"
REMOTE_DIR="${OREP_REMOTE_DIR:-/opt/orep/deploy}"
SSH=(ssh -i "$KEY" -o ConnectTimeout=20 -o ServerAliveInterval=10 -o IPQoS=none)
RSYNC_SSH="ssh -i $KEY -o ConnectTimeout=20 -o ServerAliveInterval=10 -o IPQoS=none"

echo "==> [0/5] Preflight"
test -f "$KEY" || { echo "Missing deploy key: $KEY"; exit 1; }
test -d "$PROJECT_ROOT/frontend/user" || { echo "Missing frontend/user"; exit 1; }
"${SSH[@]}" "$HOST" "test -f $REMOTE_DIR/docker-compose.release.yml && echo remote_ok"

echo "==> [1/5] Build user frontend"
cd "$PROJECT_ROOT/frontend/user"
if [ -f package-lock.json ]; then
  npm ci --prefer-offline --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi
npm run build

echo "==> [2/5] Sync into local deploy package"
cd "$PROJECT_ROOT"
rsync -a --delete frontend/user/dist/ deploy/frontend/user/dist/
mkdir -p deploy/ai-service
rsync -a ai-scoring/app/ deploy/ai-service/app/ \
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='.DS_Store' \
  --exclude='uploads/' --exclude='app/uploads/' \
  --exclude='services/ppt/agent/workspaces/' \
  --exclude='services/ppt/agent/.runtime/'
cp -f ai-scoring/main.py ai-scoring/requirements.txt ai-scoring/Dockerfile deploy/ai-service/ 2>/dev/null || true

echo "==> [3/5] Upload frontend dist + ai-service"
rsync -avz -e "$RSYNC_SSH" \
  deploy/frontend/user/dist/ \
  "$HOST:$REMOTE_DIR/frontend/user/dist/"
rsync -avz -e "$RSYNC_SSH" \
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='.DS_Store' \
  --exclude='uploads/' \
  deploy/ai-service/ \
  "$HOST:$REMOTE_DIR/ai-service/"

echo "==> [4/5] Rebuild and restart frontend-user + ai-scoring"
"${SSH[@]}" "$HOST" "cd $REMOTE_DIR && \
  docker compose --env-file .env.production -f docker-compose.release.yml build frontend-user ai-scoring && \
  docker compose --env-file .env.production -f docker-compose.release.yml up -d --no-deps frontend-user ai-scoring && \
  docker compose --env-file .env.production -f docker-compose.release.yml ps frontend-user ai-scoring"

echo "==> [5/5] Smoke check"
sleep 3
curl -skI "https://www.qvm-onestar.cn/" | head -5 || true
"${SSH[@]}" "$HOST" "cd $REMOTE_DIR && docker compose --env-file .env.production -f docker-compose.release.yml ps frontend-user ai-scoring | cat"

echo
echo "Done. Verify score report:"
echo "  https://www.qvm-onestar.cn/  → AI 评分 → 结果 / 待办 / 依据"
echo "  Hard refresh (Cmd+Shift+R) if old assets are cached."

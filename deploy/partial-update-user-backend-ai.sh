#!/usr/bin/env bash
# 将本地用户端 + Java 后端 + AI 助手服务部署到云端生产
# Usage (from Mac, project root):
#   bash deploy/partial-update-user-backend-ai.sh
#
# Covers this release:
#   - 登录页（启发·竞赛大脑 + 轻引导能力点）
#   - 首页小启 / 过程剧场 / 路由过渡
#   - 后端 clientContext 学生人设 + 诚实过程步骤
#   - ai-scoring 学生视角锁定
#
# Requires:
#   - ~/.ssh/orep_codex_deploy
#   - reachable root@39.96.213.213 (or OREP_DEPLOY_HOST / OREP_DEPLOY_KEY)
#   - local Maven + npm

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$ROOT/.." && pwd)"
HOST="${OREP_DEPLOY_HOST:-root@39.96.213.213}"
KEY="${OREP_DEPLOY_KEY:-$HOME/.ssh/orep_codex_deploy}"
REMOTE_DIR="${OREP_REMOTE_DIR:-/opt/orep/deploy}"
SSH=(ssh -i "$KEY" -o ConnectTimeout=25 -o ServerAliveInterval=15 -o IPQoS=none)
RSYNC_SSH="ssh -i $KEY -o ConnectTimeout=25 -o ServerAliveInterval=15 -o IPQoS=none"
MVN="${MVN:-$HOME/maven/bin/mvn}"
BASE_URL="${BASE_URL:-https://www.jingsaidanao.com}"

echo "==> [0/6] Preflight"
test -f "$KEY" || { echo "Missing deploy key: $KEY"; exit 1; }
test -d "$PROJECT_ROOT/frontend/user" || { echo "Missing frontend/user"; exit 1; }
test -d "$PROJECT_ROOT/backend" || { echo "Missing backend"; exit 1; }
test -d "$PROJECT_ROOT/ai-scoring" || { echo "Missing ai-scoring"; exit 1; }
command -v npm >/dev/null || { echo "npm not found"; exit 1; }
if ! command -v "$MVN" >/dev/null 2>&1 && ! command -v mvn >/dev/null 2>&1; then
  echo "Maven not found"; exit 1
fi
"${SSH[@]}" "$HOST" "test -f $REMOTE_DIR/docker-compose.release.yml && echo remote_ok"

echo "==> [1/6] Build backend jar"
cd "$PROJECT_ROOT/backend"
if command -v "$MVN" >/dev/null 2>&1; then
  "$MVN" -q -Dmaven.test.skip=true package
else
  mvn -q -Dmaven.test.skip=true package
fi
JAR="$(ls -1 target/orep-backend-*.jar 2>/dev/null | head -1)"
test -n "$JAR" && test -f "$JAR" || { echo "Backend jar missing after build"; exit 1; }
mkdir -p "$PROJECT_ROOT/deploy/backend"
cp -f "$JAR" "$PROJECT_ROOT/deploy/backend/orep-backend-1.0.0.jar"
echo "    jar=$(basename "$JAR") size=$(du -h "$PROJECT_ROOT/deploy/backend/orep-backend-1.0.0.jar" | awk '{print $1}')"

echo "==> [2/6] Build user frontend"
cd "$PROJECT_ROOT/frontend/user"
if [ -f package-lock.json ]; then
  npm ci --prefer-offline --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi
npm run build
rsync -a --delete dist/ "$PROJECT_ROOT/deploy/frontend/user/dist/"
echo "    dist files=$(find "$PROJECT_ROOT/deploy/frontend/user/dist" -type f | wc -l | tr -d ' ')"

echo "==> [3/6] Sync AI service into local deploy package"
cd "$PROJECT_ROOT"
mkdir -p deploy/ai-service
rsync -a ai-scoring/app/ deploy/ai-service/app/ \
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='.DS_Store' \
  --exclude='uploads/' --exclude='app/uploads/' \
  --exclude='services/ppt/agent/workspaces/' \
  --exclude='services/ppt/agent/.runtime/' \
  --exclude='.venv/' --exclude='node_modules/'
cp -f ai-scoring/main.py ai-scoring/requirements.txt ai-scoring/Dockerfile \
  deploy/ai-service/

echo "==> [4/6] Upload backend jar + frontend dist + ai-service"
rsync -avz -e "$RSYNC_SSH" \
  "$PROJECT_ROOT/deploy/backend/orep-backend-1.0.0.jar" \
  "$HOST:$REMOTE_DIR/backend/"
rsync -avz -e "$RSYNC_SSH" \
  --delete \
  "$PROJECT_ROOT/deploy/frontend/user/dist/" \
  "$HOST:$REMOTE_DIR/frontend/user/dist/"
rsync -avz -e "$RSYNC_SSH" \
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='.DS_Store' \
  --exclude='uploads/' \
  "$PROJECT_ROOT/deploy/ai-service/" \
  "$HOST:$REMOTE_DIR/ai-service/"

echo "==> [5/6] Rebuild & restart backend + frontend-user + ai-scoring"
"${SSH[@]}" "$HOST" "cd $REMOTE_DIR && \
  docker compose --env-file .env.production -f docker-compose.release.yml build backend frontend-user ai-scoring && \
  docker compose --env-file .env.production -f docker-compose.release.yml up -d --no-deps backend frontend-user ai-scoring && \
  docker compose --env-file .env.production -f docker-compose.release.yml ps backend frontend-user ai-scoring"

echo "==> [6/6] Smoke checks"
sleep 6
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sk "$BASE_URL/api/auth/check" >/dev/null 2>&1; then
    echo "    backend OK: $BASE_URL/api/auth/check"
    break
  fi
  echo "    waiting backend... ($i/10)"
  sleep 4
done

echo "    HEAD $BASE_URL/"
curl -skI "$BASE_URL/" | head -8 || true
echo "    HEAD $BASE_URL/login"
curl -skI "$BASE_URL/login" | head -8 || true
echo "    AI health:"
curl -sk "$BASE_URL/api/assistant/health" 2>/dev/null | head -c 400 || \
  "${SSH[@]}" "$HOST" "curl -s http://127.0.0.1:8090/api/assistant/health 2>/dev/null | head -c 400" || true
echo

"${SSH[@]}" "$HOST" "cd $REMOTE_DIR && docker compose --env-file .env.production -f docker-compose.release.yml ps backend frontend-user ai-scoring | cat"

echo
echo "Done."
echo "  User:   $BASE_URL/login"
echo "  Home:   $BASE_URL/"
echo "  Hard refresh (Cmd+Shift+R) if assets are cached."

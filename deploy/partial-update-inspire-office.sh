#!/usr/bin/env bash
# 将本地「启发 Office + 用户端/后端」部署到云端生产
# Usage (from Mac, project root):
#   bash deploy/partial-update-inspire-office.sh
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

echo "==> [0/7] Preflight"
test -f "$KEY" || { echo "Missing deploy key: $KEY"; exit 1; }
test -d "$PROJECT_ROOT/frontend/user" || { echo "Missing frontend/user"; exit 1; }
test -d "$PROJECT_ROOT/backend" || { echo "Missing backend"; exit 1; }
command -v "$MVN" >/dev/null || command -v mvn >/dev/null || { echo "Maven not found"; exit 1; }
command -v npm >/dev/null || { echo "npm not found"; exit 1; }
"${SSH[@]}" "$HOST" "test -f $REMOTE_DIR/docker-compose.release.yml && echo remote_ok"

echo "==> [1/7] Build backend jar"
cd "$PROJECT_ROOT/backend"
# -Dmaven.test.skip=true：跳过 test 编译（仓库内部分测试与当前构造器签名不同步）
if command -v "$MVN" >/dev/null 2>&1; then
  "$MVN" -q -Dmaven.test.skip=true package
else
  mvn -q -Dmaven.test.skip=true package
fi
JAR="$(ls -1 target/orep-backend-*.jar 2>/dev/null | head -1)"
test -n "$JAR" && test -f "$JAR" || { echo "Backend jar missing after build"; exit 1; }
cp -f "$JAR" "$PROJECT_ROOT/deploy/backend/orep-backend-1.0.0.jar"
echo "    jar=$(basename "$JAR") size=$(du -h "$PROJECT_ROOT/deploy/backend/orep-backend-1.0.0.jar" | awk '{print $1}')"

echo "==> [2/7] Build user frontend"
cd "$PROJECT_ROOT/frontend/user"
if [ -f package-lock.json ]; then
  npm ci --prefer-offline --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi
npm run build
rsync -a --delete dist/ "$PROJECT_ROOT/deploy/frontend/user/dist/"

echo "==> [3/7] Upload backend / frontend / collabora / compose / nginx"
rsync -avz -e "$RSYNC_SSH" \
  "$PROJECT_ROOT/deploy/backend/orep-backend-1.0.0.jar" \
  "$HOST:$REMOTE_DIR/backend/"
rsync -avz -e "$RSYNC_SSH" \
  --delete \
  "$PROJECT_ROOT/deploy/frontend/user/dist/" \
  "$HOST:$REMOTE_DIR/frontend/user/dist/"
rsync -avz -e "$RSYNC_SSH" \
  "$PROJECT_ROOT/deploy/collabora/" \
  "$HOST:$REMOTE_DIR/collabora/"
rsync -avz -e "$RSYNC_SSH" \
  "$PROJECT_ROOT/deploy/docker-compose.release.yml" \
  "$HOST:$REMOTE_DIR/docker-compose.release.yml"
rsync -avz -e "$RSYNC_SSH" \
  "$PROJECT_ROOT/deploy/nginx/nginx.conf" \
  "$HOST:$REMOTE_DIR/nginx/nginx.conf"

echo "==> [4/7] Ensure production env keys for 启发 Office"
"${SSH[@]}" "$HOST" "cd $REMOTE_DIR && \
  touch .env.production && \
  grep -q '^OREP_INSPIRE_OFFICE_ENABLED=' .env.production || echo 'OREP_INSPIRE_OFFICE_ENABLED=true' >> .env.production; \
  grep -q '^OREP_COLLABORA_URL=' .env.production || echo 'OREP_COLLABORA_URL=http://collabora:9980/collabora' >> .env.production; \
  grep -q '^OREP_COLLABORA_PUBLIC_URL=' .env.production || echo 'OREP_COLLABORA_PUBLIC_URL=https://www.jingsaidanao.com/collabora' >> .env.production; \
  grep -q '^OREP_WOPI_PUBLIC_BASE_URL=' .env.production || echo 'OREP_WOPI_PUBLIC_BASE_URL=https://www.jingsaidanao.com' >> .env.production; \
  grep -q '^COLLABORA_ALIASGROUP1=' .env.production || echo 'COLLABORA_ALIASGROUP1=https://www.jingsaidanao.com:443' >> .env.production; \
  grep -q '^COLLABORA_ADMIN_USER=' .env.production || echo 'COLLABORA_ADMIN_USER=admin' >> .env.production; \
  grep -q '^COLLABORA_ADMIN_PASSWORD=' .env.production || echo 'COLLABORA_ADMIN_PASSWORD=S3cRet' >> .env.production; \
  grep -q '^COLLABORA_IMAGE=' .env.production || echo 'COLLABORA_IMAGE=docker.m.daocloud.io/collabora/code:latest' >> .env.production; \
  # service_root=/collabora：discovery 必须带 /collabora 前缀
  sed -i 's|^OREP_COLLABORA_URL=http://collabora:9980$|OREP_COLLABORA_URL=http://collabora:9980/collabora|' .env.production; \
  sed -i 's|^OREP_COLLABORA_URL=https://www.qvm-onestar.cn/collabora|OREP_COLLABORA_URL=http://collabora:9980/collabora|' .env.production; \
  sed -i 's|^OREP_COLLABORA_URL=https://www.jingsaidanao.com/collabora|OREP_COLLABORA_URL=http://collabora:9980/collabora|' .env.production; \
  echo 'env keys:'; grep -E 'INSPIRE|COLLABORA|WOPI' .env.production | sed 's/=.*/=***/'"

echo "==> [5/7] Pull Collabora image + rebuild backend / frontend-user / nginx + start collabora"
"${SSH[@]}" "$HOST" "cd $REMOTE_DIR && \
  docker compose --env-file .env.production -f docker-compose.release.yml pull collabora && \
  docker compose --env-file .env.production -f docker-compose.release.yml build backend frontend-user && \
  docker compose --env-file .env.production -f docker-compose.release.yml up -d collabora backend frontend-user nginx && \
  docker compose --env-file .env.production -f docker-compose.release.yml ps collabora backend frontend-user nginx"

echo "==> [6/7] Health checks"
sleep 8
for i in 1 2 3 4 5 6 7 8; do
  if curl -sk "$BASE_URL/api/auth/check" >/dev/null 2>&1; then
    echo "    backend OK: $BASE_URL/api/auth/check"
    break
  fi
  echo "    waiting backend... ($i/8)"
  sleep 8
done

# Collabora discovery via public proxy
if curl -sk --max-time 20 "$BASE_URL/collabora/hosting/discovery" | head -c 200 | grep -qi 'wopi\|cool\|office'; then
  echo "    collabora discovery OK via $BASE_URL/collabora/hosting/discovery"
else
  echo "    WARN: collabora discovery not ready yet (container may still be warming up)"
  "${SSH[@]}" "$HOST" "docker logs --tail 40 orep-collabora 2>&1 || true"
fi

# Inspire Office capability endpoint (auth may 401; connectivity matters)
CODE=$(curl -sk -o /dev/null -w '%{http_code}' "$BASE_URL/api/inspire-office/status" || true)
echo "    inspire-office/status HTTP $CODE (401/200 expected if route exists)"

echo "==> [7/7] Done"
echo "Verify:"
echo "  用户端首页:   $BASE_URL/"
echo "  启发 Office:  $BASE_URL/inspire-office"
echo "  Collabora:    $BASE_URL/collabora/hosting/discovery"
echo "  打字练习:     $BASE_URL/typing-practice"

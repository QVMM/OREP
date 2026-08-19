#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MINIO_BIN="${MINIO_BIN:-$(command -v minio || true)}"
MINIO_DATA_DIR="${MINIO_DATA_DIR:-$ROOT_DIR/minio-data}"
MINIO_LOG_FILE="${MINIO_LOG_FILE:-$ROOT_DIR/logs/minio.log}"
MINIO_PID_FILE="${MINIO_PID_FILE:-$ROOT_DIR/logs/minio.pid}"
MINIO_ADDRESS="${MINIO_ADDRESS:-127.0.0.1:9000}"
MINIO_CONSOLE_ADDRESS="${MINIO_CONSOLE_ADDRESS:-127.0.0.1:9001}"
MINIO_HEALTH_URL="http://${MINIO_ADDRESS}/minio/health/live"

if curl -fsS "$MINIO_HEALTH_URL" >/dev/null 2>&1; then
  echo "MinIO is already running at http://${MINIO_ADDRESS}"
  exit 0
fi

if [ -z "$MINIO_BIN" ]; then
  echo "MinIO executable was not found. Install MinIO or set MINIO_BIN." >&2
  exit 1
fi

mkdir -p "$MINIO_DATA_DIR" "$(dirname "$MINIO_LOG_FILE")"

export MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
export MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"

nohup "$MINIO_BIN" server "$MINIO_DATA_DIR" \
  --address "$MINIO_ADDRESS" \
  --console-address "$MINIO_CONSOLE_ADDRESS" \
  >>"$MINIO_LOG_FILE" 2>&1 &
MINIO_PROCESS_ID=$!
echo "$MINIO_PROCESS_ID" > "$MINIO_PID_FILE"

for _ in $(seq 1 20); do
  if curl -fsS "$MINIO_HEALTH_URL" >/dev/null 2>&1; then
    echo "MinIO started at http://${MINIO_ADDRESS}"
    exit 0
  fi
  if ! kill -0 "$MINIO_PROCESS_ID" 2>/dev/null; then
    echo "MinIO exited during startup. Check $MINIO_LOG_FILE" >&2
    exit 1
  fi
  sleep 0.5
done

echo "MinIO did not become healthy. Check $MINIO_LOG_FILE" >&2
exit 1

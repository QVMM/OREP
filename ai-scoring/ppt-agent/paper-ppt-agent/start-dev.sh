#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$ROOT/frontend"
FRONTEND_URL="http://127.0.0.1:5173"
OREP_AI_SCORING_ENV="$ROOT/../../.env"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv was not found in the current shell environment."
  echo "Install uv or open the shell where uv works, then run sh start-dev.sh again."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm was not found in the current shell environment."
  echo "Install Node.js/npm or open the shell where npm works, then run sh start-dev.sh again."
  exit 1
fi

echo "==> Syncing backend dependencies with uv"
cd "$ROOT"
uv sync --locked

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "==> Installing frontend dependencies"
  cd "$FRONTEND_DIR"
  npm install
fi

cleanup() {
  if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "==> Starting backend"
cd "$ROOT"
if [ -f "$OREP_AI_SCORING_ENV" ]; then
  set -a
  # Reuse the parent OREP AI scoring model configuration during local integration.
  # shellcheck disable=SC1090
  . "$OREP_AI_SCORING_ENV"
  set +a
fi
MIMO_API_KEY="${MIMO_API_KEY:-${PPT_TEXT_API_KEY:-}}"
MIMO_BASE_URL="${MIMO_BASE_URL:-${PPT_TEXT_BASE_URL:-}}"
MIMO_MODEL="${MIMO_MODEL:-${PPT_TEXT_MODEL:-mimo-v2.5-pro}}"
export MIMO_API_KEY MIMO_BASE_URL MIMO_MODEL
LANG="${LANG:-zh_CN.UTF-8}" LC_ALL="${LC_ALL:-zh_CN.UTF-8}" PYTHONUTF8=1 PYTHONUNBUFFERED=1 uv run python -m uvicorn backend.app:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload \
  --reload-dir backend \
  --reload-include='*.py' &
BACKEND_PID=$!

echo "==> Starting frontend"
cd "$FRONTEND_DIR"
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort --open &
FRONTEND_PID=$!

echo
echo "Paper PPT Agent is starting:"
echo "  Backend:  http://127.0.0.1:8000"
echo "  Frontend: $FRONTEND_URL"
echo
echo "Press Ctrl+C to stop both services."

wait "$BACKEND_PID" "$FRONTEND_PID"

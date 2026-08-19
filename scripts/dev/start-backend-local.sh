#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
ENV_FILE="${OREP_BACKEND_ENV_FILE:-$BACKEND_DIR/.env.local}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing local backend env file: $ENV_FILE" >&2
  exit 1
fi

if [ -n "${OREP_JAVA_HOME:-}" ]; then
  export JAVA_HOME="$OREP_JAVA_HOME"
elif command -v /usr/libexec/java_home >/dev/null 2>&1; then
  export JAVA_HOME="$(/usr/libexec/java_home -v 21 2>/dev/null || true)"
fi

if [ -n "${JAVA_HOME:-}" ]; then
  export PATH="$JAVA_HOME/bin:$PATH"
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

mkdir -p "$BACKEND_DIR/uploads"
rm -rf "$BACKEND_DIR/target/maven-status"

"$SCRIPT_DIR/start-minio-local.sh"

echo "Starting OREP backend with env: $ENV_FILE"
echo "JAVA_HOME=${JAVA_HOME:-system default}"
cd "$BACKEND_DIR"
mvn -DskipTests -Dmaven.compiler.useIncrementalCompilation=false spring-boot:run

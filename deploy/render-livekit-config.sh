#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="${1:-$SCRIPT_DIR/../.env.production}"
TEMPLATE_FILE="${2:-$SCRIPT_DIR/livekit.prod.yaml}"
OUTPUT_FILE="${3:-$SCRIPT_DIR/livekit.rendered.yaml}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

if ! command -v envsubst >/dev/null 2>&1; then
  echo "envsubst is required. On Ubuntu: sudo apt install -y gettext-base" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

envsubst < "$TEMPLATE_FILE" > "$OUTPUT_FILE"
chmod 600 "$OUTPUT_FILE"
echo "Rendered LiveKit config: $OUTPUT_FILE"

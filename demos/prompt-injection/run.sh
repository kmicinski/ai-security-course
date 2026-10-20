#!/usr/bin/env bash
# Start the prompt-injection demo. Reads .env if present.
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a || true
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8008}"
echo "CIS400 prompt-injection demo"
echo "  backend profile : ${LLM_PROFILE:-ollama}"
echo "  open            : http://${HOST}:${PORT}"
exec uv run uvicorn app.server:app --host "$HOST" --port "$PORT" "$@"

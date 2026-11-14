#!/usr/bin/env bash
# Install what is missing, build the web page, and start Waypoint on http://127.0.0.1:8000
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x backend/.venv/bin/uvicorn ]; then
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q -r backend/requirements.txt
fi

if [ ! -f static/index.html ] || [ -n "$(find frontend/src frontend/index.html -newer static/index.html -print -quit)" ]; then
  if command -v bun >/dev/null; then (cd frontend && bun install && bun run build)
  else (cd frontend && npm install && npm run build); fi
fi

cd backend
exec .venv/bin/uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"

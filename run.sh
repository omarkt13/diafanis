#!/usr/bin/env bash
# Install what is missing, build the web page, and start Waypoint on http://127.0.0.1:8000
set -euo pipefail
cd "$(dirname "$0")"

# The app needs Python 3.11 or later. The python3 that comes with macOS is 3.9.
ok() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; }
if [ -x backend/.venv/bin/python ] && ! ok backend/.venv/bin/python; then rm -rf backend/.venv; fi
if [ ! -x backend/.venv/bin/uvicorn ]; then
  PY=""
  for c in python3.13 python3.12 python3.11 python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if command -v "$c" >/dev/null && ok "$c"; then PY="$c"; break; fi
  done
  if [ -z "$PY" ]; then
    echo "Waypoint needs Python 3.11 or later, and did not find it. On macOS: brew install python@3.13"; sleep 60; exit 1
  fi
  rm -rf backend/.venv
  "$PY" -m venv backend/.venv
  backend/.venv/bin/pip install -q --upgrade pip
  backend/.venv/bin/pip install -q -r backend/requirements.txt
fi

if [ ! -f static/index.html ] || [ -n "$(find frontend/src frontend/index.html -newer static/index.html -print -quit)" ]; then
  if command -v bun >/dev/null; then (cd frontend && bun install && bun run build)
  elif command -v npm >/dev/null; then (cd frontend && npm install && npm run build)
  else echo "Waypoint needs bun or npm to build the page, and did not find them. On macOS: brew install node"; sleep 60; exit 1; fi
fi

# HOST and PORT can also be in backend/.env
if [ -f backend/.env ]; then set -a; . backend/.env; set +a; fi
cd backend
exec .venv/bin/uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"

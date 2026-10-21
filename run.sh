#!/usr/bin/env bash
# Allswell — one-command run.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
# Call the venv's Python directly rather than relying on activation + PATH.
if [ -f .venv/Scripts/python.exe ]; then
  PY=.venv/Scripts/python.exe   # Windows (Git Bash)
else
  PY=.venv/bin/python
fi

echo "Installing dependencies..."
"$PY" -m pip install -q -r requirements.txt

echo "Starting Allswell at http://127.0.0.1:8000"
exec "$PY" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

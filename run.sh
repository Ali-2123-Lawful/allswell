#!/usr/bin/env bash
# Allswell — one-command run.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
if [ -f .venv/Scripts/activate ]; then
  source .venv/Scripts/activate   # Windows (Git Bash)
else
  source .venv/bin/activate
fi

echo "Installing dependencies..."
pip install -q -r requirements.txt

echo "Starting Allswell at http://127.0.0.1:8000"
exec uvicorn backend.main:app --host 127.0.0.1 --port 8000

#!/usr/bin/env bash
# macOS / Linux launcher
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Setting up for the first time. This downloads a few hundred MB."
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi

./.venv/bin/python app.py

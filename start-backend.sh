#!/usr/bin/env bash
# AI Code Review backend starter — works on Arch Linux, Ubuntu, Fedora, macOS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

pick_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  else
    echo ""
  fi
}

PYTHON_BIN="$(pick_python)"
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: Python 3 is not installed."
  echo "Arch Linux:  sudo pacman -S python"
  echo "Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: Git is required to clone repositories."
  echo "Arch Linux: sudo pacman -S git"
  exit 1
fi

PY_VER="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
echo "Using $PYTHON_BIN ($PY_VER)"

if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  "$PYTHON_BIN" -m venv venv
  # shellcheck disable=SC1091
  source venv/bin/activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "Created backend/.env — edit it and set OPENAI_API_KEY before demos."
  echo "  nano .env   # or use any editor"
  echo ""
fi

echo "Starting AI Code Review backend (demo mode) on http://127.0.0.1:8001 ..."
exec python run.py --demo

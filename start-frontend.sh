#!/usr/bin/env bash
# AI Code Review frontend starter — works on Arch Linux, Ubuntu, Fedora, macOS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/frontend"

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: Node.js and npm are required."
  echo "Arch Linux:  sudo pacman -S nodejs npm"
  echo "Ubuntu/Debian: sudo apt install nodejs npm"
  exit 1
fi

echo "Using Node $(node -v) / npm $(npm -v)"

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies (first run)..."
  npm install
fi

echo "Starting AI Code Review frontend..."
echo "Open http://localhost:5173 in your browser"
exec npm run dev

#!/usr/bin/env bash
set -e

PORT="${PORT:-3000}"

if [ ! -d "node_modules" ]; then
  echo "[1/2] Installing dependencies..."
  npm install
else
  echo "[1/2] Dependencies up to date."
fi


if command -v xdg-open &>/dev/null; then
  (sleep 2 && xdg-open "http://localhost:$PORT") &
elif command -v open &>/dev/null; then
  (sleep 2 && open "http://localhost:$PORT") &
fi

exec npm run dev

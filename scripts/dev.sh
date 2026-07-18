#!/usr/bin/env bash
# 本机开发：后端 + 前端 dev server
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d backend/.venv ]]; then
  python3 -m venv backend/.venv
fi
source backend/.venv/bin/activate
pip install -q -r backend/requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

if [[ ! -d frontend/node_modules ]]; then
  (cd frontend && npm install)
fi

echo "启动后端 http://127.0.0.1:8000"
(cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
BACK_PID=$!

echo "启动前端 http://127.0.0.1:5173"
(cd frontend && npm run dev) &
FRONT_PID=$!

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null' EXIT INT TERM
wait

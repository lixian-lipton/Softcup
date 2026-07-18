#!/usr/bin/env bash
# 生产模式：构建前端，由后端统一托管
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

source backend/.venv/bin/activate
pip install -q -r backend/requirements.txt

cd frontend
npm install
npm run build
cd ..

echo "构建完成。启动："
echo "  cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "访问 http://<host>:8000"

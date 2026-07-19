#!/usr/bin/env bash
# 将管理员口令重置为 123456（或 ADMIN_PASSWORD）
# 用法：bash scripts/reset_admin_password.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STOP="$ROOT/deploy/launcher/stop-softcup.sh"
START="$ROOT/deploy/launcher/start-softcup.sh"
VENV="$ROOT/backend/.venv"

if [[ -x "$STOP" ]]; then
  bash "$STOP" >/dev/null 2>&1 || true
fi

export SOFTCUP_RESET_ADMIN_PASSWORD=1
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-123456}"

cd "$ROOT/backend"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python3 - <<'PY'
from app.database import init_db
init_db()
print("管理员密码已重置为环境变量 ADMIN_PASSWORD（默认 123456）")
PY

if [[ -x "$START" ]]; then
  bash "$START"
fi

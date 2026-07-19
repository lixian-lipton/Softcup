#!/usr/bin/env bash
# 桌面快捷方式入口：重启服务并打开浏览器
# 每次启动都会先停旧进程再拉起，避免重装后仍跑着内存里的旧后端（表现为登录 405）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="$ROOT/backend/.venv"
LOG_DIR="$ROOT/data"
LOG_FILE="$LOG_DIR/softcup.log"
PID_FILE="$LOG_DIR/softcup.pid"
STOP_SCRIPT="$(cd "$(dirname "$0")" && pwd)/stop-softcup.sh"
HOST="127.0.0.1"
PORT="8000"
URL="http://${HOST}:${PORT}"

mkdir -p "$LOG_DIR"

notify() {
  local msg="$1"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send -a "设备检修系统" "$msg" || true
  fi
  echo "$msg"
}

if [[ ! -x "$VENV/bin/uvicorn" ]]; then
  notify "尚未安装，请先运行安装程序 install.run / install.sh"
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="设备检修系统" --text="尚未安装运行环境。\n请先执行 install.run 或项目目录下的 install.sh" || true
  fi
  exit 1
fi

is_up() {
  curl -fsS --connect-timeout 1 --max-time 2 "$URL/api/health" >/dev/null 2>&1
}

has_login_api() {
  # OPTIONS/POST 探测：旧后端无 /api/auth/login 时会对 POST 返回 405
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 1 --max-time 3 \
    -X POST "$URL/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{}' 2>/dev/null || echo 000)"
  # 422=参数校验失败（接口存在）；401/400/403=业务错误；405/404=旧后端
  [[ "$code" == "422" || "$code" == "401" || "$code" == "400" || "$code" == "403" ]]
}

notify "正在重启设备检修系统…"
bash "$STOP_SCRIPT" >/dev/null 2>&1 || true
sleep 0.5

(
  cd "$ROOT/backend"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  : >"$LOG_FILE"
  nohup uvicorn app.main:app --host 0.0.0.0 --port "$PORT" \
    >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
)

for _ in $(seq 1 50); do
  if is_up; then
    break
  fi
  sleep 0.4
done

if ! is_up; then
  notify "启动失败，请查看日志: $LOG_FILE"
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="设备检修系统" --text="启动失败。\n日志: $LOG_FILE" || true
  fi
  exit 1
fi

if ! has_login_api; then
  notify "后端登录接口不可用，请重新执行 install.run 覆盖安装后再启动"
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="设备检修系统" \
      --text="检测到后端缺少登录接口（常见于未重启旧进程）。\n请重新运行 install.run，然后再次双击桌面图标。" || true
  fi
  exit 1
fi

notify "服务已就绪，正在打开浏览器"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v gio >/dev/null 2>&1; then
  gio open "$URL" >/dev/null 2>&1 || true
elif command -v firefox >/dev/null 2>&1; then
  firefox "$URL" >/dev/null 2>&1 &
fi

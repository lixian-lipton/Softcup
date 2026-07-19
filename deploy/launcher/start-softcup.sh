#!/usr/bin/env bash
# 桌面快捷方式入口：启动服务并打开浏览器
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="$ROOT/backend/.venv"
LOG_DIR="$ROOT/data"
LOG_FILE="$LOG_DIR/softcup.log"
PID_FILE="$LOG_DIR/softcup.pid"
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
  notify "尚未安装，请先运行安装程序 install.sh"
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="设备检修系统" --text="尚未安装运行环境。\n请先双击或执行项目目录下的 install.sh" || true
  fi
  exit 1
fi

is_up() {
  curl -fsS --connect-timeout 1 --max-time 2 "$URL/api/health" >/dev/null 2>&1
}

if ! is_up; then
  # 清理失效 pid
  if [[ -f "$PID_FILE" ]]; then
    old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "${old_pid}" ]] && ! kill -0 "$old_pid" 2>/dev/null; then
      rm -f "$PID_FILE"
    fi
  fi

  notify "正在启动设备检修系统…"
  (
    cd "$ROOT/backend"
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    nohup uvicorn app.main:app --host 0.0.0.0 --port "$PORT" \
      >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
  )

  for _ in $(seq 1 40); do
    if is_up; then
      break
    fi
    sleep 0.5
  done
fi

if is_up; then
  notify "服务已就绪，正在打开浏览器"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
  elif command -v gio >/dev/null 2>&1; then
    gio open "$URL" >/dev/null 2>&1 || true
  elif command -v firefox >/dev/null 2>&1; then
    firefox "$URL" >/dev/null 2>&1 &
  fi
else
  notify "启动失败，请查看日志: $LOG_FILE"
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="设备检修系统" --text="启动失败。\n日志: $LOG_FILE" || true
  fi
  exit 1
fi

#!/usr/bin/env bash
# 设备检修系统 — 一键安装程序（银河麒麟 / LoongArch）
# 用法：在项目根目录执行  bash install.sh   或  ./install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

APP_NAME="设备检修系统"
ICON_SRC="$ROOT/设备检修系统.png"
LAUNCHER_DIR="$ROOT/deploy/launcher"
START_SCRIPT="$LAUNCHER_DIR/start-softcup.sh"
STOP_SCRIPT="$LAUNCHER_DIR/stop-softcup.sh"
DESKTOP_IN="$LAUNCHER_DIR/softcup.desktop.in"
MARKER="$ROOT/.softcup_installed"

log()  { echo -e "\033[1;32m[安装]\033[0m $*"; }
warn() { echo -e "\033[1;33m[提示]\033[0m $*"; }
err()  { echo -e "\033[1;31m[错误]\033[0m $*" >&2; }

banner() {
  cat <<'EOF'

  ================================================
    设备检修知识检索与作业系统  — 安装程序
  ================================================

EOF
}

detect_desktop_dir() {
  local d
  for d in "$HOME/桌面" "$HOME/Desktop" "$(xdg-user-dir DESKTOP 2>/dev/null || true)"; do
    if [[ -n "${d}" && -d "${d}" ]]; then
      echo "$d"
      return 0
    fi
  done
  mkdir -p "$HOME/桌面"
  echo "$HOME/桌面"
}

trust_desktop_file() {
  local f="$1"
  # 银河麒麟 / GNOME 需标记为可信任才可双击运行
  if command -v gio >/dev/null 2>&1; then
    gio set "$f" metadata::trusted true 2>/dev/null || true
  fi
  chmod +x "$f"
}

install_deps() {
  log "安装 Python 运行依赖（离线优先）…"
  if [[ ! -d "$ROOT/deploy/offline-wheels" ]]; then
    err "未找到 deploy/offline-wheels，请使用完整发布包"
    exit 1
  fi
  bash "$ROOT/scripts/vm_install.sh" --offline
}

prepare_runtime() {
  log "准备运行时文件…"
  if [[ ! -f "$ROOT/.env" && -f "$ROOT/.env.example" ]]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
  fi
  if [[ ! -f "$ROOT/data/search.db" ]]; then
    warn "未找到 data/search.db，检索库为空。请从完整包拷贝该文件。"
  else
    log "检索索引已就绪: data/search.db"
  fi
  if [[ ! -f "$ROOT/frontend/dist/index.html" ]]; then
    warn "未找到 frontend/dist，Web 页面可能无法显示。"
  else
    log "前端产物已就绪: frontend/dist"
  fi
  if [[ ! -f "$ICON_SRC" ]]; then
    err "未找到图标: $ICON_SRC"
    exit 1
  fi
  chmod +x "$START_SCRIPT" "$STOP_SCRIPT" "$ROOT/scripts/vm_install.sh"
}

install_shortcut() {
  local desktop_dir apps_dir icon_dst desktop_file apps_file
  desktop_dir="$(detect_desktop_dir)"
  apps_dir="$HOME/.local/share/applications"
  icon_dst="$HOME/.local/share/icons/softcup-设备检修系统.png"
  mkdir -p "$apps_dir" "$(dirname "$icon_dst")"

  log "安装图标 → $icon_dst"
  cp -f "$ICON_SRC" "$icon_dst"

  desktop_file="$desktop_dir/${APP_NAME}.desktop"
  apps_file="$apps_dir/softcup-maintenance.desktop"

  log "生成桌面快捷方式 → $desktop_file"
  # Desktop Entry 的 Exec 对含空格路径需加引号
  local start_exec stop_exec
  start_exec="$START_SCRIPT"
  stop_exec="$STOP_SCRIPT"
  if [[ "$start_exec" == *" "* ]]; then start_exec="\"${START_SCRIPT}\""; fi
  if [[ "$stop_exec" == *" "* ]]; then stop_exec="\"${STOP_SCRIPT}\""; fi

  sed \
    -e "s|@START_SCRIPT@|${start_exec}|g" \
    -e "s|@STOP_SCRIPT@|${stop_exec}|g" \
    -e "s|@ICON_PATH@|${icon_dst}|g" \
    -e "s|@INSTALL_ROOT@|${ROOT}|g" \
    "$DESKTOP_IN" >"$desktop_file"

  cp -f "$desktop_file" "$apps_file"
  trust_desktop_file "$desktop_file"
  trust_desktop_file "$apps_file"

  # 部分环境需要去掉“不允许启动”标记
  if command -v dbus-launch >/dev/null 2>&1; then
    true
  fi

  echo "$ROOT" >"$MARKER"
  echo "$desktop_file" >"$ROOT/.softcup_desktop_path"
  log "快捷方式已创建。若桌面图标无法双击，请右键 → 允许启动 / 信任。"
}

maybe_gui() {
  if command -v zenity >/dev/null 2>&1; then
    zenity --info --title="$APP_NAME" --width=420 --text \
      "安装完成！\n\n桌面已生成「${APP_NAME}」图标。\n双击图标即可启动系统并打开浏览器。\n\n安装目录:\n${ROOT}" \
      || true
  fi
}

main() {
  banner
  log "安装目录: $ROOT"
  log "系统: $(uname -s) $(uname -m)"

  if ! command -v python3 >/dev/null 2>&1; then
    err "未找到 python3。请先: sudo yum install -y python3"
    exit 1
  fi

  # 覆盖安装前先停掉旧进程，避免继续占用旧代码（登录会报 Method Not Allowed）
  if [[ -x "$STOP_SCRIPT" ]]; then
    log "停止已有服务（如有）…"
    bash "$STOP_SCRIPT" >/dev/null 2>&1 || true
  fi

  prepare_runtime
  install_deps
  install_shortcut

  cat <<EOF

  ------------------------------------------------
  安装成功
  ------------------------------------------------
  桌面图标: ${APP_NAME}
  启动方式: 双击桌面图标，或执行:
            ${START_SCRIPT}
  停止服务: ${STOP_SCRIPT}
  访问地址: http://127.0.0.1:8000
  管理员口令: 首次启动后见 ${ROOT}/data/INITIAL_ADMIN.txt
              （切勿将口令展示在登录页或对外文档）
  ------------------------------------------------

EOF
  maybe_gui
}

main "$@"

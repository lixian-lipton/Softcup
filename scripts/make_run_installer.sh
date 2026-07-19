#!/usr/bin/env bash
# 在本机打包「商业风格」自解压安装程序 *.run
# 用法：bash scripts/make_run_installer.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT_DIR="$ROOT/deploy"
OUT_RUN="$OUT_DIR/install.run"
STAGE="${TMPDIR:-/tmp}/softcup_run_pack_$$"
# 清理历史中文名安装包，统一为 install.run
rm -f "$OUT_DIR/设备检修系统-安装程序.run"

rm -rf "$STAGE"
mkdir -p "$STAGE/Softcup"

echo "==> 收集发布文件"
tar -C "$ROOT" \
  --exclude='.git' \
  --exclude='backend/.venv' \
  --exclude='frontend/node_modules' \
  --exclude='deploy/_bundle_stage' \
  --exclude='deploy/softcup-loongarch-bundle.tar.gz' \
  --exclude='deploy/*.run' \
  --exclude='data/uploads' \
  --exclude='data/*.log' \
  --exclude='data/softcup.pid' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  -cf - . | tar -C "$STAGE/Softcup" -xf -

test -f "$STAGE/Softcup/install.sh"
test -f "$STAGE/Softcup/设备检修系统.png"
test -d "$STAGE/Softcup/deploy/offline-wheels"
test -f "$STAGE/Softcup/data/search.db"
test -f "$STAGE/Softcup/frontend/dist/index.html"

chmod +x "$STAGE/Softcup/install.sh" \
  "$STAGE/Softcup/scripts/"*.sh \
  "$STAGE/Softcup/deploy/launcher/"*.sh

ARCHIVE="$STAGE/payload.tar.gz"
tar -czf "$ARCHIVE" -C "$STAGE" Softcup

echo "==> 生成自解压安装程序"
{
  cat <<'HEADER'
#!/usr/bin/env bash
# 设备检修系统 — 自解压安装程序
set -euo pipefail

APP="设备检修系统"
echo ""
echo "================================================"
echo "  ${APP} 安装程序"
echo "================================================"
echo ""

TARGET="${SOFTCUP_INSTALL_DIR:-$HOME/${APP}}"
echo "将安装到: $TARGET"
echo "（可通过环境变量 SOFTCUP_INSTALL_DIR 修改）"
echo ""
read -r -p "按回车开始安装，Ctrl+C 取消… " _

mkdir -p "$TARGET"
ARCHIVE_LINE=$(awk '/^__SOFTCUP_ARCHIVE__$/ {print NR + 1; exit 0;}' "$0")
tail -n +"$ARCHIVE_LINE" "$0" | tar -xz -C "$TARGET" --strip-components=1

chmod +x "$TARGET/install.sh" "$TARGET/deploy/launcher/"*.sh "$TARGET/scripts/"*.sh
cd "$TARGET"
bash ./install.sh

echo ""
echo "安装程序结束。可关闭本窗口，从桌面图标启动 ${APP}。"
exit 0
__SOFTCUP_ARCHIVE__
HEADER
  cat "$ARCHIVE"
} >"$OUT_RUN"

chmod +x "$OUT_RUN"
rm -rf "$STAGE"

ls -lh "$OUT_RUN"
echo "完成。将此 .run 拷到虚机后执行:"
echo "  chmod +x ./install.run"
echo "  ./install.run"

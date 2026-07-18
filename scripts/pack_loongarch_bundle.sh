#!/usr/bin/env bash
# 在本机打包，供拷贝到 LoongArch 虚机
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OUT_DIR="$ROOT/deploy"
BUNDLE_NAME="softcup-loongarch-bundle.tar.gz"
STAGE="${TMPDIR:-/tmp}/softcup_loongarch_bundle_$$"

rm -rf "$STAGE"
mkdir -p "$STAGE/Softcup-main"

if [[ ! -f data/search.db ]]; then
  echo "错误: 缺少 data/search.db，请先运行 python scripts/ingest_pdf.py"
  exit 1
fi
if [[ ! -d frontend/dist ]]; then
  echo "错误: 缺少 frontend/dist，请先 npm run build"
  exit 1
fi
if [[ ! -d deploy/offline-wheels ]] || [[ -z "$(ls -A deploy/offline-wheels)" ]]; then
  echo "错误: 缺少 deploy/offline-wheels"
  exit 1
fi

echo "==> 复制文件到暂存目录"
for item in backend frontend scripts docs .env.example README.md A1题目.txt; do
  if [[ -e "$item" ]]; then
    cp -a "$item" "$STAGE/Softcup-main/"
  fi
done

# deploy：只带说明与离线包，不带暂存目录/旧压缩包
mkdir -p "$STAGE/Softcup-main/deploy/offline-wheels"
cp -a deploy/offline-wheels/. "$STAGE/Softcup-main/deploy/offline-wheels/"
if [[ -f deploy/LOONGARCH部署.md ]]; then
  cp -a deploy/LOONGARCH部署.md "$STAGE/Softcup-main/deploy/"
fi

mkdir -p "$STAGE/Softcup-main/data/uploads"
cp -a data/search.db "$STAGE/Softcup-main/data/"
if [[ -f data/app.db ]]; then
  cp -a data/app.db "$STAGE/Softcup-main/data/"
fi

rm -rf "$STAGE/Softcup-main/backend/.venv"
rm -rf "$STAGE/Softcup-main/frontend/node_modules"
find "$STAGE/Softcup-main" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "$STAGE/Softcup-main" -type d -name '.venv' -exec rm -rf {} + 2>/dev/null || true

if [[ -f "摩托车发动机维修手册.pdf" ]]; then
  cp -a "摩托车发动机维修手册.pdf" "$STAGE/Softcup-main/" || true
fi

chmod +x "$STAGE/Softcup-main/scripts/"*.sh 2>/dev/null || true

echo "==> 打包 $OUT_DIR/$BUNDLE_NAME"
tar -czf "$OUT_DIR/$BUNDLE_NAME" -C "$STAGE" Softcup-main
rm -rf "$STAGE"

ls -lh "$OUT_DIR/$BUNDLE_NAME"
echo "完成。请将该文件拷到虚机后："
echo "  tar -xzf softcup-loongarch-bundle.tar.gz"
echo "  cd Softcup-main && bash scripts/vm_install.sh"
echo "详见 deploy/LOONGARCH部署.md"

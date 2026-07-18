#!/usr/bin/env bash
# LoongArch / 银河麒麟虚机依赖安装（跳过 pymupdf）
# 用法：
#   cd Softcup-main
#   bash scripts/vm_install.sh
#   bash scripts/vm_install.sh --offline   # 仅用 deploy/offline-wheels
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OFFLINE=0
if [[ "${1:-}" == "--offline" ]]; then
  OFFLINE=1
fi

WHEEL_DIR="$ROOT/deploy/offline-wheels"
REQ="$ROOT/backend/requirements-vm.txt"

echo "==> 项目目录: $ROOT"
echo "==> Python: $(python3 --version) arch=$(uname -m)"

if [[ ! -d backend/.venv ]]; then
  python3 -m venv backend/.venv
fi
# shellcheck disable=SC1091
source backend/.venv/bin/activate
python -m pip install -U pip setuptools wheel

probe() {
  local url="$1"
  if curl -fsSIL --connect-timeout 5 --max-time 15 "$url" >/dev/null 2>&1; then
    echo "  OK  $url"
    return 0
  fi
  echo "  FAIL $url"
  return 1
}

install_online() {
  local index="$1"
  local host
  host="$(echo "$index" | sed -E 's|https?://([^/]+)/.*|\1|')"
  echo "==> 尝试在线安装: $index"
  pip install -r "$REQ" -i "$index" --trusted-host "$host" \
    --timeout 120 --retries 5
}

install_offline() {
  if [[ ! -d "$WHEEL_DIR" ]] || [[ -z "$(ls -A "$WHEEL_DIR" 2>/dev/null || true)" ]]; then
    echo "错误: 未找到离线包目录 $WHEEL_DIR"
    echo "请先从本机拷贝 deploy/offline-wheels/ 到虚机。"
    exit 1
  fi
  echo "==> 离线安装（来自 $WHEEL_DIR）"
  echo "提示: pydantic-core / greenlet / sqlalchemy 源码包需本机有 gcc；"
  echo "      pydantic-core 还需要 rustc（可用: curl https://sh.rustup.rs -sSf | sh）"
  pip install --no-index --find-links="$WHEEL_DIR" \
    pip setuptools wheel packaging tomli pathspec || true
  pip install --no-index --find-links="$WHEEL_DIR" -r "$REQ"
}

if [[ "$OFFLINE" -eq 1 ]]; then
  install_offline
else
  echo "==> 探测 PyPI 连通性"
  CAN_ONLINE=0
  probe "https://pypi.org/simple/fastapi/" && CAN_ONLINE=1 || true
  probe "https://pypi.tuna.tsinghua.edu.cn/simple/fastapi/" || true
  probe "https://mirrors.aliyun.com/pypi/simple/fastapi/" || true
  probe "https://mirrors.cloud.tencent.com/pypi/simple/fastapi/" || true

  if [[ "$CAN_ONLINE" -eq 1 ]] || probe "https://pypi.org/simple/fastapi/"; then
    install_online "https://pypi.org/simple" || true
  fi

  if ! python -c "import fastapi" 2>/dev/null; then
    install_online "https://mirrors.aliyun.com/pypi/simple" || true
  fi
  if ! python -c "import fastapi" 2>/dev/null; then
    install_online "https://mirrors.cloud.tencent.com/pypi/simple" || true
  fi
  if ! python -c "import fastapi" 2>/dev/null; then
    install_online "https://pypi.tuna.tsinghua.edu.cn/simple" || true
  fi
  if ! python -c "import fastapi" 2>/dev/null; then
    echo "==> 在线安装失败，回退离线包"
    install_offline
  fi
fi

echo "==> 验证关键模块"
python - <<'PY'
import importlib
for m in ("fastapi", "uvicorn", "pydantic", "sqlalchemy", "httpx"):
    importlib.import_module(m)
    print("  OK", m)
print("全部依赖可用")
PY

echo
echo "下一步（勿再运行 ingest_pdf，LoongArch 无 pymupdf）："
echo "  1) 确认 data/search.db 已从本机拷贝"
echo "  2) 若无 frontend/dist，执行: cd frontend && npm install && npm run build"
echo "  3) cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"

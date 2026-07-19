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
  echo "提示: 核心依赖均为 wheel，无需 Cython/Rust；系统包装请用 yum。"

  pip install --no-index --find-links="$WHEEL_DIR" \
    pip setuptools wheel packaging tomli

  # 核心包（均为 wheel，无需编译）
  pip install --no-index --find-links="$WHEEL_DIR" \
    fastapi==0.99.1 \
    pydantic==1.10.22 \
    uvicorn==0.34.0 \
    starlette==0.27.0 \
    anyio==3.7.1 \
    sniffio==1.3.1 \
    idna==3.10 \
    typing-extensions==4.12.2 \
    click==8.1.8 \
    h11==0.14.0 \
    httpx==0.27.2 \
    httpcore==1.0.7 \
    certifi==2024.12.14 \
    "SQLAlchemy==2.0.36" \
    python-multipart==0.0.20 \
    aiofiles==24.1.0 \
    python-dotenv==1.0.1

  # greenlet 可选：缺 Python.h 时直接跳过，避免 pip 刷两次长错误
  _py_inc="$(python -c 'import sysconfig; print(sysconfig.get_path("include") or "")' 2>/dev/null || true)"
  if [[ -n "${_py_inc}" && -f "${_py_inc}/Python.h" ]] && command -v g++ >/dev/null 2>&1; then
    echo "==> 检测到 Python.h / g++，安装可选依赖 greenlet"
    pip install --no-index --find-links="$WHEEL_DIR" greenlet==3.1.1
  else
    echo "==> 跳过 greenlet（缺少 Python 开发头文件或 g++）。"
    echo "    本项目同步 API 不依赖它，可直接启动服务。"
    echo "    若仍要安装: sudo yum install -y gcc gcc-c++ make python3-devel"
    echo "    然后重新执行: bash scripts/vm_install.sh --offline"
  fi
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
try:
    import greenlet  # noqa: F401
    print("  OK greenlet（可选）")
except Exception:
    print("  SKIP greenlet（可选，未安装不影响当前同步服务）")
print("关键依赖可用，可以启动服务")
PY

echo
echo "下一步（勿再运行 ingest_pdf，LoongArch 无 pymupdf）："
echo "  1) 确认 data/search.db 存在"
echo "  2) 确认 frontend/dist 存在（zip/仓库里一般已有）"
echo "  3) cd backend && source ../backend/.venv/bin/activate"
echo "     uvicorn app.main:app --host 0.0.0.0 --port 8000"

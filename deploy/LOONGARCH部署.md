# LoongArch + 银河麒麟 部署说明

## 现象说明

虚机上出现：

```text
No matching distribution found for fastapi>=0.115.0 (from versions: none)
```

在 **loongarch64** 上通常表示：**访问不了该 PyPI 镜像的包列表**（网络/防火墙），不是版本号写错。  
`pymupdf` 则是 LoongArch **确实没有** 可用包，不要在虚机上装。

## 推荐流程（拷贝离线包）

### 1. 在本机准备并打包

本仓库已提供：

- `deploy/offline-wheels/`：可跨架构的纯 Python wheel + 需编译的源码包
- `data/search.db`：已导入手册的检索库
- `frontend/dist/`：已构建前端
- `scripts/vm_install.sh`：虚机安装脚本
- `backend/requirements-vm.txt`：无 pymupdf 的依赖列表

在本机执行：

```bash
cd /data/xli/softcup
bash scripts/pack_loongarch_bundle.sh
# 生成 deploy/softcup-loongarch-bundle.tar.gz
```

把该压缩包拷到虚机（U 盘 / scp）。

### 2. 在虚机解压并安装

```bash
cd ~/桌面
tar -xzf softcup-loongarch-bundle.tar.gz
cd Softcup-main   # 或解压出的目录名

# 先看网络能不能访问官方 PyPI
curl -I https://pypi.org/simple/fastapi/

# 安装依赖（自动：在线多源 → 失败则离线）
bash scripts/vm_install.sh

# 若确认无外网，强制离线：
# bash scripts/vm_install.sh --offline
```

离线安装 `pydantic-core` 需要编译工具：

```bash
# 银河麒麟 / 类 RHEL
sudo yum install -y gcc gcc-c++ make python3-devel openssl-devel
# 若提示需要 Rust：
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
bash scripts/vm_install.sh --offline
```

### 3. 启动（不要再跑 ingest_pdf）

```bash
cp -n .env.example .env
# 确认索引存在
ls -lh data/search.db

cd backend
source ../backend/.venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器：`http://127.0.0.1:8000`  
自检：`curl http://127.0.0.1:8000/api/stats`（`total_chunks` 应 > 0）

## 若仍要在线安装

不要用会返回空列表的镜像。优先官方源：

```bash
source backend/.venv/bin/activate
python -m pip install -U pip
pip install -r backend/requirements-vm.txt -i https://pypi.org/simple
```

## 不要做的事

- 不要在虚机执行 `pip install pymupdf` / `python scripts/ingest_pdf.py`
- 不要使用从 x86 拷来的 `backend/.venv`
- 不要使用 x86 的 `manylinux_x86_64.whl`（本仓库 offline-wheels 已避免）

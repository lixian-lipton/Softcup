# LoongArch + 银河麒麟 部署说明

## 虚机环境约定

- 系统包用 **yum** 安装（银河麒麟），不要用 apt。
- 虚机已有 **python3 / pip**；项目依赖优先 `scripts/vm_install.sh --offline`（`deploy/offline-wheels`）。
- 需要编译工具时再用 yum，例如：`sudo yum install -y gcc gcc-c++ make python3-devel`。

## 一键安装程序（推荐）

本机打包自解压安装包：

```bash
cd /data/xli/softcup
bash scripts/make_run_installer.sh
# 生成 deploy/install.run
```

虚机上：

```bash
chmod +x ./install.run
./install.run
```

或已解压源码目录时：

```bash
cd Softcup-main   # 或安装目录
chmod +x install.sh
./install.sh
```

安装完成后桌面会出现 **「设备检修系统」** 图标（图标文件：`设备检修系统.png`）。  
双击图标 → 自动启动后端并打开浏览器。右键快捷方式可选「停止服务」。

### 账号说明

- **管理员**：首次启动自动创建，默认 `admin` / `123456`（登录页不展示；登录后可在右上角「修改密码」更改）。
- **普通用户**：在登录页自行注册，登录后同样可修改密码。
- 若管理员口令丢失：在安装目录执行 `bash scripts/reset_admin_password.sh` 可恢复为 `123456`。

管理员可审核案例与人工意见、上传知识文件；普通用户可检索/作业、提交案例与意见。

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

当前离线包已避开 Rust/`pydantic-core`/`Cython`。若仅 `greenlet` 编译失败：

```bash
# 银河麒麟 / 类 RHEL（可选，用于 greenlet）
sudo yum install -y gcc gcc-c++ make python3-devel
bash scripts/vm_install.sh --offline
```

无 gcc 时也可先启动服务；同步检索/问答一般仍可用。

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

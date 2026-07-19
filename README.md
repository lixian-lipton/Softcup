# 设备检修知识检索与作业系统

Soft Cup A1 赛题 — 本机先行开发，后续迁移至 LoongArch + 银河麒麟。

## 本机启动（第一步）

```bash
cd /data/xli/softcup
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
```

验证：

- 健康检查：http://127.0.0.1:8000/api/health
- API 文档：http://127.0.0.1:8000/docs

## 开发进度

- [x] 第一步：项目骨架 + 后端最小可运行基座
- [x] 第二步：PDF 手册解析 + SQLite FTS 检索
- [x] 第三步：大模型接入 + RAG 问答
- [x] 第四步A：作业指引 + 知识沉淀 + 标注 + 图片问答 API
- [x] 第四步B：前端 Vue3 三页
- [x] 第四步C：检索召回、离线 RAG、上传安全、作业闭环、图谱摘要与文档增强
- [ ] 第五步：虚机部署 + 比赛文档

## 当前能力概览

- 多模态检索：文本 + 设备型号 + 图片描述，返回来源、页码、相似度和引用片段。
- RAG 问答：`mock` 模式也会基于命中证据生成离线诊断；`api` 模式预留 DeepSeek Key。
- 作业指引：按检修等级生成步骤、工具、安全项、检查点、预计时长和完成进度。
- 知识沉淀：案例审核通过后写入检索索引，并生成设备/部件/故障/方案图谱。
- 安全控制：图片上传限制 JPG/PNG/WebP 和大小，LLM 上下文截断降低 token 开销。

## 第二步：导入手册并检索

```bash
source backend/.venv/bin/activate
pip install -r backend/requirements.txt   # 若尚未安装 pymupdf
python scripts/ingest_pdf.py            # 导入 PDF（纯本地）
python scripts/ingest_pdf.py --force      # 重新导入

cd backend && uvicorn app.main:app --reload --port 8000
```

测试：

```bash
curl http://127.0.0.1:8000/api/stats
curl -X POST http://127.0.0.1:8000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"机油","top_k":3}'
```

索引文件位置：`data/search.db`（运行时自动生成）

本地核心链路 smoke test：

```bash
source backend/.venv/bin/activate
python scripts/smoke_test.py
python scripts/api_smoke_test.py
```

## 第三步：RAG 智能问答

### 模式说明

| LLM_MODE | 说明 |
|----------|------|
| `mock` | 默认，不加载模型，用于联调 |
| `local` | 加载 `/data/xli/Qwen3.5-0.8B`（只读） |
| `api` | 调用 DeepSeek，需在 `.env` 填写 `LLM_API_KEY` |

### 安装本地推理依赖（我方可执行，需联网下载）

```bash
source backend/.venv/bin/activate
pip install -r backend/requirements-local.txt
```

包装位置：`backend/.venv/lib/python3.13/site-packages/`

### 启动与测试

```bash
cp .env.example .env   # 按需修改 LLM_MODE / LLM_API_KEY
cd backend && uvicorn app.main:app --reload --port 8000

curl -X POST http://127.0.0.1:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"火花塞怎么检查","top_k":3}'
```

### DeepSeek API 配置（获得 Key 后）

编辑 `.env`：

```env
LLM_MODE=api
LLM_API_KEY=sk-你的key
LLM_API_BASE=https://api.deepseek.com/v1
LLM_API_MODEL=deepseek-chat
```

## 第四步A：作业指引与知识管理

```bash
curl -X POST http://127.0.0.1:8000/api/workflow \
  -H 'Content-Type: application/json' \
  -d '{"device_model":"摩托车发动机","maintenance_level":"level1","fault_description":"火花塞"}'

curl -X POST http://127.0.0.1:8000/api/cases \
  -F "title=怠速不稳" -F "device_model=摩托车发动机" \
  -F "symptom=冷启动怠速波动" -F "solution=清洁节气门"

curl -X POST http://127.0.0.1:8000/api/cases/1/review \
  -H 'Content-Type: application/json' -d '{"approve":true}'
curl http://127.0.0.1:8000/api/graph
```

业务库：`data/app.db`；上传目录：`data/uploads/`

## 第四步B：前端 Web 界面

### 开发模式（推荐）

```bash
chmod +x scripts/dev.sh scripts/build.sh
./scripts/dev.sh
```

- 前端：http://127.0.0.1:5173
- 后端：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs

### 生产模式（单端口）

```bash
./scripts/build.sh
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
# 访问 http://127.0.0.1:8000
```

前端依赖安装位置：`frontend/node_modules/`

## 比赛文档草案

- `docs/01-需求分析.md`
- `docs/02-概要设计.md`
- `docs/03-测试报告.md`
- `docs/04-运行部署说明.md`

## LoongArch 虚机部署

LoongArch 上 **无法安装 pymupdf**，且部分 PyPI 镜像会返回 `from versions: none`。请使用离线包或一键安装程序。

### 一键安装（推荐）

```bash
# 本机生成安装程序
bash scripts/make_run_installer.sh
# 将 deploy/install.run 拷到虚机：
chmod +x ./install.run
./install.run
```

安装后桌面生成「设备检修系统」图标，双击即可启动。也可在源码目录执行 `./install.sh`。

首次启动会创建管理员账号，初始口令写入安装目录 `data/INITIAL_ADMIN.txt`（界面不展示口令）。也可预先设置环境变量 `ADMIN_PASSWORD`。

详见 `deploy/LOONGARCH部署.md`。

## 环境说明

- Python 虚拟环境：`backend/.venv/`（仅在本项目目录内）
- 第三步接本地 Qwen 时可改用 conda；第二步无网络依赖
- 模型路径占位：`LOCAL_MODEL_PATH`（见 `.env.example`）

## 目录结构

```
softcup/
├── backend/       # FastAPI 后端
├── frontend/      # Vue3 前端
├── scripts/       # dev.sh / build.sh / ingest_pdf.py
├── deploy/        # 部署脚本（待补充）
├── docs/          # 比赛文档（待补充）
└── data/          # 运行时数据（自动生成，不提交）
```

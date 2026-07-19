import mimetypes
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi.responses import Response

from app.config import ROOT_DIR, UPLOAD_DIR, settings
from app.database import init_db
from app.routers import auth, knowledge, search, system, workflow

app = FastAPI(
    title=settings.app_name,
    version="0.6.0",
    description="Soft Cup A1 — 设备检修知识检索与作业系统",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(workflow.router)
app.include_router(knowledge.router)

frontend_dist = ROOT_DIR / "frontend" / "dist"


def _safe_file(base: Path, relative: str) -> Path | None:
    base = base.resolve()
    target = (base / relative).resolve()
    if not target.is_file() or not target.is_relative_to(base):
        return None
    return target


def _file_response(path: Path) -> Response:
    media_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return Response(path.read_bytes(), media_type=media_type)


@app.get("/uploads/{filename}", include_in_schema=False)
async def uploaded_file(filename: str):
    path = _safe_file(UPLOAD_DIR, filename)
    if not path:
        raise HTTPException(status_code=404, detail="文件不存在")
    return _file_response(path)


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str):
    if not frontend_dist.exists():
        raise HTTPException(status_code=404, detail="前端尚未构建")
    target = _safe_file(frontend_dist, path) if path else None
    if not target:
        target = frontend_dist / "index.html"
    return _file_response(target)


@app.on_event("startup")
def on_startup():
    init_db()

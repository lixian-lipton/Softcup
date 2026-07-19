import platform

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import SEARCH_DB, settings
from app.schemas import SourceStat, StatsResponse
from app.services.llm import llm_service
from app.services.search_store import search_store

router = APIRouter(tags=["系统"])


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str = "0.6.2"
    platform: str
    arch: str
    note: str
    indexed_chunks: int
    llm_mode: str
    model_loaded: bool
    local_model_path: str
    load_error: str | None = None
    auth_enabled: bool = True


@router.get("/api/health", response_model=HealthResponse)
async def health():
    arch = platform.machine()
    note = "服务运行正常"
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version="0.6.2",
        platform=platform.system(),
        arch=arch,
        note=note,
        indexed_chunks=search_store.count,
        llm_mode=settings.llm_mode,
        model_loaded=llm_service.model_loaded,
        local_model_path=settings.local_model_path,
        load_error=llm_service.load_error,
        auth_enabled=True,
    )


@router.get("/api/stats", response_model=StatsResponse, tags=["检索"])
async def stats():
    return StatsResponse(
        total_chunks=search_store.count,
        db_path=str(SEARCH_DB),
        sources=[SourceStat(**s) for s in search_store.stats_by_source()],
    )

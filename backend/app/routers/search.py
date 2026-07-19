from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.deps import get_current_user
from app.models import User
from app.schemas import (
    AskRequest,
    AskResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from app.services.llm import llm_service
from app.services.rag import rag_ask
from app.services.search_store import search_store
from app.services.uploads import save_image_upload

router = APIRouter(tags=["检索", "智能问答"])


@router.post("/api/search", response_model=SearchResponse, tags=["检索"])
async def search(req: SearchRequest, _: User = Depends(get_current_user)):
    hits_raw = search_store.search(
        query=req.query,
        top_k=req.top_k,
        device_model=req.device_model,
    )
    hits = [SearchHit(**h) for h in hits_raw]
    return SearchResponse(
        hits=hits,
        total_in_store=search_store.count,
        query_terms=search_store.query_terms(req.query),
    )


@router.post("/api/ask", response_model=AskResponse, tags=["智能问答"])
async def ask(req: AskRequest, _: User = Depends(get_current_user)):
    return await rag_ask(
        query=req.query,
        device_model=req.device_model,
        top_k=req.top_k,
    )


@router.post("/api/ask/image", response_model=AskResponse, tags=["智能问答"])
async def ask_with_image(
    query: str = Form(...),
    device_model: str | None = Form(None),
    top_k: int = Form(5, ge=1, le=20),
    image: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    save_path = await save_image_upload(image, prefix="ask")
    image_desc, _ = await llm_service.describe_image(str(save_path))
    response = await rag_ask(
        query=query,
        device_model=device_model,
        top_k=top_k,
        image_description=image_desc,
    )
    return response

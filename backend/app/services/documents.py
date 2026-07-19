from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import UPLOAD_DIR, settings
from app.services.search_store import search_store

TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".log"}
PDF_SUFFIXES = {".pdf"}


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _extract_pdf_text(path: Path) -> list[tuple[int, str]]:
    try:
        import fitz  # type: ignore
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="当前环境无法解析 PDF（缺少 pymupdf）。请上传 TXT/MD 文本，或在本机导入手册。",
        ) from exc
    doc = fitz.open(path)
    pages: list[tuple[int, str]] = []
    for i in range(len(doc)):
        pages.append((i + 1, doc[i].get_text("text")))
    doc.close()
    return pages


async def save_knowledge_file(upload: UploadFile, prefix: str = "doc") -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in TEXT_SUFFIXES | PDF_SUFFIXES:
        raise HTTPException(status_code=415, detail="仅支持 TXT/MD/PDF 知识文件")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    dest = UPLOAD_DIR / f"{prefix}_{uuid.uuid4().hex}{suffix}"
    written = 0
    try:
        with dest.open("wb") as f:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件不能超过 {settings.max_upload_mb}MB",
                    )
                f.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    if written == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="上传文件为空")
    return dest


def ingest_saved_document(
    path: Path,
    *,
    device_model: str,
    title: str | None = None,
) -> tuple[str, int]:
    source = title or path.name
    search_store.delete_by_source(source)

    texts: list[str] = []
    metas: list[dict] = []
    ids: list[str] = []
    suffix = path.suffix.lower()

    if suffix in PDF_SUFFIXES:
        pages = _extract_pdf_text(path)
        for page, content in pages:
            for i, chunk in enumerate(chunk_text(content)):
                if len(chunk) < 30:
                    continue
                cid = f"doc-{uuid.uuid4().hex}"
                texts.append(chunk)
                metas.append(
                    {
                        "source": source,
                        "page": page,
                        "device_model": device_model,
                        "doc_type": "manual",
                        "chunk_index": i,
                    }
                )
                ids.append(cid)
    else:
        content = path.read_text(encoding="utf-8", errors="ignore")
        for i, chunk in enumerate(chunk_text(content)):
            if len(chunk) < 20:
                continue
            cid = f"doc-{uuid.uuid4().hex}"
            texts.append(chunk)
            metas.append(
                {
                    "source": source,
                    "page": None,
                    "device_model": device_model,
                    "doc_type": "manual",
                    "chunk_index": i,
                }
            )
            ids.append(cid)

    if not texts:
        raise HTTPException(status_code=400, detail="未能从文件中提取有效文本")

    n = search_store.add_documents(texts, metas, ids)
    return source, n

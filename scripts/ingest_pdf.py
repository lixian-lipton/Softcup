#!/usr/bin/env python3
"""将 PDF 维修手册切块并写入本地 SQLite FTS 索引（纯本地，无需网络）。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import fitz  # noqa: E402

from app.config import ROOT_DIR  # noqa: E402
from app.services.search_store import SearchStore  # noqa: E402

DEFAULT_PDF = ROOT_DIR / "摩托车发动机维修手册.pdf"


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


def ingest_pdf(
    store: SearchStore,
    pdf_path: Path,
    device_model: str,
    source_name: str | None = None,
    force: bool = False,
) -> int:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")

    source = source_name or pdf_path.name
    if force:
        store.delete_by_source(source)

    doc = fitz.open(pdf_path)
    batch_texts: list[str] = []
    batch_metas: list[dict] = []
    total = 0

    def flush() -> None:
        nonlocal total
        if batch_texts:
            total += store.add_documents(batch_texts, batch_metas)
            batch_texts.clear()
            batch_metas.clear()

    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text")
        for i, chunk in enumerate(chunk_text(text)):
            if len(chunk) < 30:
                continue
            batch_texts.append(chunk)
            batch_metas.append(
                {
                    "source": source,
                    "page": page_num + 1,
                    "device_model": device_model,
                    "doc_type": "manual",
                    "chunk_index": i,
                }
            )
            if len(batch_texts) >= 64:
                flush()
        if (page_num + 1) % 20 == 0:
            print(f"  已处理 {page_num + 1}/{len(doc)} 页...")

    flush()
    doc.close()
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="导入 PDF 到本地 FTS 索引")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="PDF 路径")
    parser.add_argument("--device-model", default="摩托车发动机")
    parser.add_argument("--force", action="store_true", help="覆盖同 source 的旧数据")
    args = parser.parse_args()

    store = SearchStore()
    n = ingest_pdf(
        store,
        args.pdf,
        device_model=args.device_model,
        force=args.force,
    )
    print(f"本次导入 {n} 块，索引总量: {store.count}")
    print(f"索引文件: {store.db_path}")


if __name__ == "__main__":
    main()

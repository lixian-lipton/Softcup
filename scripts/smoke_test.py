#!/usr/bin/env python3
"""Local smoke test for core retrieval, RAG and workflow services."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.rag import rag_ask  # noqa: E402
from app.services.search_store import search_store  # noqa: E402
from app.services.workflow import build_workflow  # noqa: E402


async def main() -> None:
    print(f"index_count={search_store.count}")
    assert search_store.count > 0, "search index is empty; run scripts/ingest_pdf.py first"

    hits = search_store.search("火花塞怎么检查", top_k=3, device_model="摩托车发动机")
    print(f"search_hits={len(hits)}")
    assert hits, "expected retrieval hits for 火花塞"

    answer = await rag_ask("火花塞怎么检查", device_model="摩托车发动机", top_k=3)
    print(f"rag_hits={len(answer.hits)} confidence={answer.confidence} risk={answer.risk_level}")
    assert answer.hits, "expected RAG citations"
    assert answer.answer, "expected non-empty answer"

    workflow = await build_workflow("摩托车发动机", "level1", "火花塞")
    print(
        "workflow_steps="
        f"{len(workflow.steps)} risk={workflow.risk_level} evidence={len(workflow.evidence_hits)}"
    )
    assert workflow.steps, "expected workflow steps"

    print("smoke_test=ok")


if __name__ == "__main__":
    asyncio.run(main())

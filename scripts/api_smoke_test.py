#!/usr/bin/env python3
"""HTTP-level smoke test without opening a listening port."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402


async def main() -> None:
    init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        health = await asyncio.wait_for(client.get("/api/health"), timeout=5)
        print("health", health.status_code, health.json()["status"], flush=True)
        assert health.status_code == 200

        stats = await asyncio.wait_for(client.get("/api/stats"), timeout=5)
        print("stats", stats.status_code, stats.json()["total_chunks"], flush=True)
        assert stats.status_code == 200

        search = await asyncio.wait_for(
            client.post(
                "/api/search",
                json={"query": "火花塞怎么检查", "device_model": "摩托车发动机", "top_k": 2},
            ),
            timeout=5,
        )
        print("search", search.status_code, len(search.json()["hits"]), flush=True)
        assert search.status_code == 200
        assert search.json()["hits"]

        ask = await asyncio.wait_for(
            client.post(
                "/api/ask",
                json={"query": "火花塞怎么检查", "device_model": "摩托车发动机", "top_k": 2},
            ),
            timeout=5,
        )
        print("ask", ask.status_code, ask.json()["confidence"], flush=True)
        assert ask.status_code == 200

        workflow = await asyncio.wait_for(
            client.post(
                "/api/workflow",
                json={
                    "device_model": "摩托车发动机",
                    "maintenance_level": "level1",
                    "fault_description": "火花塞",
                },
            ),
            timeout=5,
        )
        print("workflow", workflow.status_code, len(workflow.json()["steps"]), flush=True)
        assert workflow.status_code == 200

        frontend = await asyncio.wait_for(client.get("/"), timeout=5)
        print("frontend", frontend.status_code, flush=True)
        assert frontend.status_code in {200, 307}

    print("api_smoke_test=ok", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

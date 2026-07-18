from __future__ import annotations

import hashlib
import re
import sqlite3
from typing import Any

from app.config import SEARCH_DB

DOMAIN_TERMS = (
    "火花塞",
    "机油",
    "压缩压力",
    "起动电机",
    "发动机",
    "气缸",
    "活塞",
    "离合器",
    "机油泵",
    "水泵",
    "曲轴",
    "平衡轴",
    "传动",
    "气门",
    "凸轮轴",
    "涨紧器",
    "磁电机",
    "空气滤清器",
    "节气门",
    "怠速",
    "异响",
    "漏油",
    "渗漏",
    "冷却液",
    "电极",
    "间隙",
    "积碳",
    "拆卸",
    "安装",
    "检查",
    "调整",
)


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        item = item.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _extract_query_terms(query: str) -> list[str]:
    """Extract useful Chinese/English query terms for FTS and LIKE fallback."""
    parts = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", query)
    terms: list[str] = []

    for term in DOMAIN_TERMS:
        if term in query:
            terms.append(term)

    for part in parts:
        if re.fullmatch(r"[a-zA-Z0-9]+", part):
            if len(part) > 1:
                terms.append(part)
            continue
        if len(part) <= 8:
            terms.append(part)
            continue
        for size in (4, 3, 2):
            for start in range(0, max(0, len(part) - size + 1)):
                terms.append(part[start : start + size])
                if len(terms) >= 20:
                    return _dedupe_keep_order(terms)

    return _dedupe_keep_order(terms)[:20]


def _build_fts_query(terms: list[str]) -> str:
    return " OR ".join(f'"{t.replace(chr(34), chr(34) + chr(34))}"' for t in terms[:16])


class SearchStore:
    """SQLite FTS5 全文检索，纯本地、无需网络。"""

    def __init__(self, db_path=SEARCH_DB) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS doc_meta (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    page INTEGER,
                    device_model TEXT,
                    doc_type TEXT,
                    chunk_index INTEGER
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(
                    content,
                    id UNINDEXED,
                    tokenize='unicode61'
                );
                """
            )

    @property
    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM doc_meta").fetchone()
            return int(row["c"]) if row else 0

    def stats_by_source(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT source, doc_type, COUNT(*) AS count
                FROM doc_meta
                GROUP BY source, doc_type
                ORDER BY count DESC, source
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def query_terms(self, query: str) -> list[str]:
        return _extract_query_terms(query)

    def clear_all(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM documents")
            conn.execute("DELETE FROM doc_meta")
            conn.commit()

    def delete_by_source(self, source: str) -> None:
        with self._connect() as conn:
            ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM doc_meta WHERE source = ?", (source,)
                ).fetchall()
            ]
            for doc_id in ids:
                conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                conn.execute("DELETE FROM doc_meta WHERE id = ?", (doc_id,))
            conn.commit()

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> int:
        if not texts:
            return 0
        if ids is None:
            ids = [
                hashlib.md5(
                    f"{m.get('source', '')}:{m.get('page', '')}:{i}:{t[:80]}".encode()
                ).hexdigest()
                for i, (t, m) in enumerate(zip(texts, metadatas))
            ]
        with self._connect() as conn:
            for doc_id, text, meta in zip(ids, texts, metadatas):
                conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                conn.execute("DELETE FROM doc_meta WHERE id = ?", (doc_id,))
                conn.execute(
                    """
                    INSERT INTO doc_meta (id, source, page, device_model, doc_type, chunk_index)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        meta.get("source", "unknown"),
                        meta.get("page"),
                        meta.get("device_model"),
                        meta.get("doc_type"),
                        meta.get("chunk_index"),
                    ),
                )
                conn.execute(
                    "INSERT INTO documents (content, id) VALUES (?, ?)",
                    (text, doc_id),
                )
            conn.commit()
        return len(texts)

    def search(
        self,
        query: str,
        top_k: int = 5,
        device_model: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.count == 0:
            return []

        terms = _extract_query_terms(query)
        if not terms:
            terms = [query.strip()[:40]]
        fts_q = _build_fts_query(terms)
        sql = """
            SELECT d.content, d.id, m.source, m.page, m.device_model, m.doc_type,
                   bm25(documents) AS rank
            FROM documents d
            JOIN doc_meta m ON d.id = m.id
            WHERE documents MATCH ?
        """
        params: list[Any] = [fts_q]
        if device_model:
            sql += " AND m.device_model = ?"
            params.append(device_model)
        sql += " ORDER BY rank LIMIT ?"
        params.append(top_k)

        try:
            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            rows = []

        if not rows:
            like_terms = [t for t in terms if len(t) >= 2][:8] or [query.strip()[:40]]
            like_sql = " OR ".join("d.content LIKE ?" for _ in like_terms)
            like_params: list[Any] = [f"%{t}%" for t in like_terms]
            sql = f"""
                SELECT d.content, d.id, m.source, m.page, m.device_model, m.doc_type,
                       0 AS rank
                FROM documents d
                JOIN doc_meta m ON d.id = m.id
                WHERE ({like_sql})
            """
            if device_model:
                sql += " AND m.device_model = ?"
                like_params.append(device_model)
            sql += " LIMIT ?"
            like_params.append(top_k)
            with self._connect() as conn:
                rows = conn.execute(sql, like_params).fetchall()

        hits: list[dict[str, Any]] = []
        for row in rows:
            rank = float(row["rank"]) if row["rank"] is not None else 0.0
            score = round(max(0.1, min(1.0, 1.0 / (1.0 + abs(rank) / 10.0))), 4)
            hits.append(
                {
                    "id": row["id"],
                    "content": row["content"],
                    "source": row["source"],
                    "page": row["page"],
                    "score": score,
                    "device_model": row["device_model"],
                    "doc_type": row["doc_type"],
                }
            )
        return hits


search_store = SearchStore()

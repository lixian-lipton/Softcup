from __future__ import annotations

import re

from app.config import settings
from app.schemas import AskResponse, SearchHit
from app.services.llm import llm_service
from app.services.search_store import search_store

HIGH_RISK_TERMS = ("冒烟", "明火", "燃油", "泄漏", "漏油", "高温", "烧焦", "紧急", "无法制动")
MEDIUM_RISK_TERMS = ("异响", "无法启动", "熄火", "怠速", "过热", "压力", "电气")


def _risk_level(text: str) -> str:
    if any(term in text for term in HIGH_RISK_TERMS):
        return "high"
    if any(term in text for term in MEDIUM_RISK_TERMS):
        return "medium"
    return "low"


def _workflow_level(risk_level: str) -> str:
    if risk_level == "high":
        return "emergency"
    if risk_level == "medium":
        return "level1"
    return "daily"


def _confidence(hits: list[SearchHit]) -> float:
    if not hits:
        return 0.12
    top_scores = [h.score for h in hits[:3]]
    base = sum(top_scores) / len(top_scores)
    coverage_bonus = min(0.12, len(hits) * 0.02)
    return round(min(0.95, max(0.2, base + coverage_bonus)), 2)


def _citation(hit: SearchHit) -> str:
    page = f"第 {hit.page} 页" if hit.page else "案例"
    return f"{hit.source}（{page}）"


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？；])|\s{2,}", text)
    return [p.strip() for p in parts if p.strip()]


def _evidence_lines(query: str, hits: list[SearchHit]) -> list[str]:
    terms = search_store.query_terms(query)
    lines: list[str] = []
    for hit in hits[:4]:
        sentences = _split_sentences(hit.content)
        selected = [
            s for s in sentences if any(term and term in s for term in terms[:10])
        ]
        if not selected:
            selected = sentences[:1]
        for sentence in selected[:2]:
            short = sentence[:160]
            if short not in lines:
                lines.append(short)
        if len(lines) >= 5:
            break
    return lines


def _offline_answer(
    query: str,
    hits: list[SearchHit],
    risk: str,
    image_description: str | None,
) -> str:
    if not hits:
        return (
            "当前知识库没有命中足够相关的手册或案例。\n\n"
            "可能原因：问题描述过宽、关键词与手册目录不一致，或手册尚未导入。\n\n"
            "建议排查步骤：\n"
            "1. 换用部件名、故障现象、检修动作组合检索，例如“火花塞 检查”或“机油 泄漏”；\n"
            "2. 确认已运行 scripts/ingest_pdf.py 导入维修手册；\n"
            "3. 若现场存在高温、燃油泄漏、冒烟等风险，先停机隔离再处理。\n\n"
            "安全注意事项：信息不足时不要直接拆检关键部件。"
        )

    evidence = _evidence_lines(query, hits)
    citations = [_citation(h) for h in hits[:3]]
    risk_text = {"high": "高", "medium": "中", "low": "低"}.get(risk, "未知")

    lines = [
        f"风险等级：{risk_text}。以下建议仅基于当前命中的手册/案例片段。",
        "",
        "可能原因：",
    ]
    if image_description:
        lines.append(f"- 图片线索显示：{image_description}")
    for item in evidence[:3]:
        lines.append(f"- 手册/案例提到：{item}")

    lines.extend(
        [
            "",
            "建议排查步骤：",
            "1. 先停机、断电并确认发动机冷却，记录故障现象和设备型号；",
            "2. 按引用片段定位对应部件，优先检查外观、连接、间隙、磨损和污染情况；",
            "3. 若发现超差、裂纹、严重积碳、泄漏或异常磨损，按手册流程调整或更换；",
            "4. 处理后进行复检和试运行，记录结果并沉淀为检修案例。",
            "",
            "安全注意事项：",
            "- 涉及燃油、机油、高温或旋转部件时，禁止带故障强行运转；",
            "- 检修中使用匹配工具，拆装方向和力矩以完整手册为准；",
            "- 若引用片段不足以覆盖现场情况，应查阅完整手册或升级给班组长确认。",
            "",
            "引用依据：",
        ]
    )
    lines.extend(f"- {c}" for c in citations)
    return "\n".join(lines)


async def rag_ask(
    query: str,
    device_model: str | None = None,
    top_k: int = 5,
    image_description: str | None = None,
) -> AskResponse:
    combined_query = query
    if device_model:
        combined_query = f"设备型号：{device_model}。{combined_query}"
    if image_description:
        combined_query = f"{combined_query}\n图像描述：{image_description}"

    hits_raw = search_store.search(
        query=combined_query,
        top_k=top_k,
        device_model=device_model,
    )
    hits = [SearchHit(**h) for h in hits_raw]
    risk = _risk_level(f"{query} {image_description or ''}")
    confidence = _confidence(hits)
    citations = [_citation(h) for h in hits[:5]]
    suggested_actions = [
        "断电/停机并确认现场安全",
        "按引用页码复核手册步骤",
        "记录异常与处理结果",
    ]
    if risk == "high":
        suggested_actions.insert(1, "隔离燃油/高温/泄漏风险并上报")

    context = "\n\n".join(
        f"[引用 {i}: {h.source}, 页码: {h.page or '案例'}, 相似度: {h.score}]\n{h.content}"
        for i, h in enumerate(hits[:5], start=1)
    )
    user_prompt = (
        f"用户问题：{query}\n"
        f"设备型号：{device_model or '未指定'}\n"
        f"风险等级：{risk}\n\n"
        f"检索到的维修手册/案例片段：\n"
        f"{context or '（暂无检索结果，请先运行 scripts/ingest_pdf.py 导入手册）'}"
    )
    if image_description:
        user_prompt = f"{user_prompt}\n\n图像描述：{image_description}"

    offline_answer = _offline_answer(query, hits, risk, image_description)
    answer = offline_answer
    fallback_reason = None

    if settings.llm_mode.lower() != "mock":
        generated, fallback_reason = await llm_service.generate(user_prompt)
        answer = generated if not fallback_reason else offline_answer

    return AskResponse(
        answer=answer,
        hits=hits,
        llm_mode=settings.llm_mode.lower(),
        model_loaded=llm_service.model_loaded,
        fallback_reason=fallback_reason,
        image_description=image_description,
        confidence=confidence,
        risk_level=risk,
        citations=citations,
        suggested_actions=suggested_actions,
        suggested_workflow_level=_workflow_level(risk),
    )

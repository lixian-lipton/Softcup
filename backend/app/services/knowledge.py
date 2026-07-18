from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditStatus, CaseStudy, KnowledgeEntity, KnowledgeRelation
from app.services.search_store import search_store

PART_TERMS = (
    "火花塞",
    "节气门",
    "空气滤清器",
    "机油泵",
    "水泵",
    "气门",
    "凸轮轴",
    "活塞",
    "气缸",
    "离合器",
    "曲轴",
    "平衡轴",
    "起动电机",
    "磁电机",
)


def add_case_to_search_index(case: CaseStudy) -> None:
    text = (
        f"检修案例：{case.title}\n"
        f"设备型号：{case.device_model}\n"
        f"故障现象：{case.symptom}\n"
        f"处理方案：{case.solution}"
    )
    search_store.add_documents(
        texts=[text],
        metadatas=[
            {
                "source": f"case:{case.id}",
                "page": None,
                "device_model": case.device_model,
                "doc_type": "case",
                "chunk_index": 0,
            }
        ],
        ids=[f"case-{case.id}"],
    )


def _get_or_create_entity(
    db: Session, name: str, entity_type: str, description: str | None
) -> KnowledgeEntity:
    entity = (
        db.query(KnowledgeEntity)
        .filter(KnowledgeEntity.name == name, KnowledgeEntity.entity_type == entity_type)
        .first()
    )
    if entity:
        return entity
    entity = KnowledgeEntity(name=name, entity_type=entity_type, description=description)
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def _get_or_create_relation(
    db: Session, source_id: int, target_id: int, relation_type: str
) -> None:
    exists = (
        db.query(KnowledgeRelation)
        .filter_by(source_id=source_id, target_id=target_id, relation_type=relation_type)
        .first()
    )
    if exists:
        return
    db.add(
        KnowledgeRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
        )
    )
    db.commit()


def upsert_graph_from_case(db: Session, case: CaseStudy) -> None:
    device = _get_or_create_entity(db, case.device_model, "device", "设备")
    fault = _get_or_create_entity(db, case.symptom[:80], "fault", case.symptom)
    procedure = _get_or_create_entity(db, case.title, "procedure", case.solution[:200])
    _get_or_create_relation(db, device.id, fault.id, "has_fault")
    _get_or_create_relation(db, fault.id, procedure.id, "resolved_by")

    combined = f"{case.title} {case.symptom} {case.solution}"
    for part_name in PART_TERMS:
        if part_name not in combined:
            continue
        part = _get_or_create_entity(db, part_name, "part", f"{case.device_model}相关部件")
        _get_or_create_relation(db, device.id, part.id, "contains")
        _get_or_create_relation(db, part.id, fault.id, "related_to")


def approve_case(db: Session, case: CaseStudy) -> None:
    case.status = AuditStatus.approved
    add_case_to_search_index(case)
    upsert_graph_from_case(db, case)


def reject_case(db: Session, case: CaseStudy) -> None:
    case.status = AuditStatus.rejected

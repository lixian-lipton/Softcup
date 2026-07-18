from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Annotation, AuditStatus, CaseStudy, KnowledgeEntity, KnowledgeRelation
from app.schemas import (
    AnnotationCreate,
    AnnotationOut,
    AnnotationRecord,
    CaseOut,
    CaseReview,
    GraphEdge,
    GraphNode,
    GraphResponse,
)
from app.services.knowledge import approve_case, reject_case
from app.services.uploads import save_image_upload

router = APIRouter(prefix="/api", tags=["知识管理"])


@router.get("/cases", response_model=list[CaseOut])
async def list_cases(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(CaseStudy).order_by(CaseStudy.created_at.desc())
    if status:
        try:
            audit_status = AuditStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="未知审核状态") from exc
        q = q.filter(CaseStudy.status == audit_status)
    return q.limit(100).all()


@router.post("/cases", response_model=CaseOut)
async def create_case(
    title: str = Form(..., min_length=1, max_length=120),
    device_model: str = Form(..., min_length=1, max_length=128),
    symptom: str = Form(..., min_length=1, max_length=1000),
    solution: str = Form(..., min_length=1, max_length=2000),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    image_path = None
    if image and image.filename:
        dest = await save_image_upload(image, prefix="case")
        image_path = str(dest)

    case = CaseStudy(
        title=title,
        device_model=device_model,
        symptom=symptom,
        solution=solution,
        image_path=image_path,
        status=AuditStatus.pending,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.post("/cases/{case_id}/review", response_model=CaseOut)
async def review_case(case_id: int, body: CaseReview, db: Session = Depends(get_db)):
    case = db.query(CaseStudy).filter(CaseStudy.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案例不存在")
    if body.approve:
        approve_case(db, case)
    else:
        reject_case(db, case)
    case.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(case)
    return case


@router.post("/annotations", response_model=AnnotationOut)
async def create_annotation(body: AnnotationCreate, db: Session = Depends(get_db)):
    ann = Annotation(**body.model_dump())
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return AnnotationOut(id=ann.id)


@router.get("/annotations", response_model=list[AnnotationRecord])
async def list_annotations(db: Session = Depends(get_db)):
    return db.query(Annotation).order_by(Annotation.created_at.desc()).limit(100).all()


@router.get("/graph", response_model=GraphResponse)
async def get_graph(db: Session = Depends(get_db)):
    nodes = db.query(KnowledgeEntity).all()
    edges = db.query(KnowledgeRelation).all()
    summary: dict[str, int] = {}
    for node in nodes:
        summary[node.entity_type] = summary.get(node.entity_type, 0) + 1
    return GraphResponse(
        nodes=[
            GraphNode(
                id=n.id,
                name=n.name,
                entity_type=n.entity_type,
                description=n.description,
            )
            for n in nodes
        ],
        edges=[
            GraphEdge(
                id=e.id,
                source=e.source_id,
                target=e.target_id,
                relation_type=e.relation_type,
            )
            for e in edges
        ],
        summary=summary,
    )

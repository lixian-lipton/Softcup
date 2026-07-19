from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Annotation, AuditStatus, CaseStudy, KnowledgeEntity, KnowledgeRelation, User
from app.schemas import (
    AnnotationCreate,
    AnnotationOut,
    AnnotationRecord,
    CaseOut,
    CaseReview,
    DocumentIngestResult,
    GraphEdge,
    GraphNode,
    GraphResponse,
)
from app.services.documents import ingest_saved_document, save_knowledge_file
from app.services.knowledge import approve_annotation, approve_case, reject_annotation, reject_case
from app.services.uploads import save_image_upload

router = APIRouter(prefix="/api", tags=["知识管理"])


def _username_map(db: Session, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    rows = db.query(User).filter(User.id.in_(user_ids)).all()
    return {u.id: u.username for u in rows}


def _case_out(case: CaseStudy, authors: dict[int, str]) -> CaseOut:
    return CaseOut(
        id=case.id,
        title=case.title,
        device_model=case.device_model,
        symptom=case.symptom,
        solution=case.solution,
        image_path=case.image_path,
        image_url=case.image_url,
        status=case.status.value if hasattr(case.status, "value") else str(case.status),
        user_id=case.user_id,
        author=authors.get(case.user_id) if case.user_id else None,
        created_at=case.created_at,
        reviewed_at=case.reviewed_at,
    )


def _ann_out(ann: Annotation, authors: dict[int, str]) -> AnnotationRecord:
    status = ann.status.value if hasattr(ann.status, "value") else str(getattr(ann, "status", "pending") or "pending")
    return AnnotationRecord(
        id=ann.id,
        query=ann.query,
        original_answer=ann.original_answer,
        corrected_answer=ann.corrected_answer,
        rating=ann.rating,
        source_refs=ann.source_refs,
        status=status,
        user_id=ann.user_id,
        author=authors.get(ann.user_id) if ann.user_id else None,
        created_at=ann.created_at,
        reviewed_at=getattr(ann, "reviewed_at", None),
    )


def _body_dict(body) -> dict:
    if hasattr(body, "model_dump"):
        return body.model_dump()
    return body.dict()


@router.get("/cases", response_model=list[CaseOut])
async def list_cases(
    status: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(CaseStudy).order_by(CaseStudy.created_at.desc())
    if mine or user.role.value == "user":
        q = q.filter(CaseStudy.user_id == user.id)
    if status:
        try:
            audit_status = AuditStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="未知审核状态") from exc
        q = q.filter(CaseStudy.status == audit_status)
    cases = q.limit(100).all()
    authors = _username_map(db, {c.user_id for c in cases if c.user_id})
    return [_case_out(c, authors) for c in cases]


@router.post("/cases", response_model=CaseOut)
async def create_case(
    title: str = Form(..., min_length=1, max_length=120),
    device_model: str = Form(..., min_length=1, max_length=128),
    symptom: str = Form(..., min_length=1, max_length=1000),
    solution: str = Form(..., min_length=1, max_length=2000),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
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
        user_id=user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return _case_out(case, {user.id: user.username})


@router.post("/cases/{case_id}/review", response_model=CaseOut)
async def review_case(
    case_id: int,
    body: CaseReview,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
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
    authors = _username_map(db, {case.user_id} if case.user_id else set())
    return _case_out(case, authors)


@router.post("/annotations", response_model=AnnotationOut)
async def create_annotation(
    body: AnnotationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = _body_dict(body)
    ann = Annotation(**data, user_id=user.id, status=AuditStatus.pending)
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return AnnotationOut(id=ann.id, message="意见已提交，等待管理员审核")


@router.get("/annotations", response_model=list[AnnotationRecord])
async def list_annotations(
    status: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Annotation).order_by(Annotation.created_at.desc())
    if mine or user.role.value == "user":
        q = q.filter(Annotation.user_id == user.id)
    if status:
        try:
            audit_status = AuditStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="未知审核状态") from exc
        q = q.filter(Annotation.status == audit_status)
    rows = q.limit(100).all()
    authors = _username_map(db, {a.user_id for a in rows if a.user_id})
    return [_ann_out(a, authors) for a in rows]


@router.post("/annotations/{ann_id}/review", response_model=AnnotationRecord)
async def review_annotation(
    ann_id: int,
    body: CaseReview,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    ann = db.query(Annotation).filter(Annotation.id == ann_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="标注不存在")
    if body.approve:
        approve_annotation(ann)
    else:
        reject_annotation(ann)
    ann.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(ann)
    authors = _username_map(db, {ann.user_id} if ann.user_id else set())
    return _ann_out(ann, authors)


@router.post("/knowledge/documents", response_model=DocumentIngestResult)
async def upload_knowledge_document(
    device_model: str = Form("摩托车发动机"),
    title: str | None = Form(None),
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
):
    path = await save_knowledge_file(file, prefix="knowledge")
    source, n = ingest_saved_document(path, device_model=device_model, title=title or file.filename)
    return DocumentIngestResult(
        source=source,
        chunks=n,
        message=f"已入库 {n} 个文本块，可立即检索",
    )


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
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

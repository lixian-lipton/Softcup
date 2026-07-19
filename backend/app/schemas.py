from datetime import datetime

import pydantic
from pydantic import BaseModel, Field

_PYDANTIC_V2 = int(pydantic.VERSION.split(".", 1)[0]) >= 2

if _PYDANTIC_V2:
    from pydantic import ConfigDict


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=300, description="故障描述或检索关键词")
    device_model: str | None = Field(None, max_length=128, description="设备型号，可选过滤")
    top_k: int = Field(5, ge=1, le=20)


class SearchHit(BaseModel):
    id: str
    content: str
    source: str
    page: int | None = None
    score: float
    device_model: str | None = None
    doc_type: str | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    total_in_store: int
    query_terms: list[str] = Field(default_factory=list)


class SourceStat(BaseModel):
    source: str
    doc_type: str | None = None
    count: int


class StatsResponse(BaseModel):
    total_chunks: int
    db_path: str
    sources: list[SourceStat] = Field(default_factory=list)


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=300, description="检修问题或故障描述")
    device_model: str | None = Field(None, max_length=128, description="设备型号")
    top_k: int = Field(5, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    hits: list[SearchHit]
    llm_mode: str
    model_loaded: bool
    fallback_reason: str | None = None
    image_description: str | None = None
    confidence: float = 0.0
    risk_level: str = "unknown"
    citations: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    suggested_workflow_level: str | None = None


class WorkflowStep(BaseModel):
    order: int
    title: str
    description: str
    tools: list[str] = Field(default_factory=list)
    compliance: list[str] = Field(default_factory=list)
    required: bool = True
    checkpoint: str | None = None


class WorkflowRequest(BaseModel):
    device_model: str = Field(..., min_length=1, max_length=128)
    maintenance_level: str = Field(..., min_length=1, max_length=32)
    fault_description: str | None = Field(None, max_length=300)


class WorkflowResponse(BaseModel):
    workflow_name: str
    device_model: str
    maintenance_level: str
    steps: list[WorkflowStep]
    safety_notes: list[str]
    llm_summary: str
    risk_level: str = "medium"
    estimated_minutes: int = 30
    progress_rule: str = "必填步骤全部确认后方可归档"
    evidence_hits: list[SearchHit] = Field(default_factory=list)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6, max_length=64)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=64)
    # 登录身份：必须与账号在库中的角色一致（界面显式选择，而非仅靠用户名判断）
    login_as: str = Field("user", description="user 或 admin")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64)


class UserOut(BaseModel):
    id: int
    username: str
    role: str

    if _PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:

        class Config:
            orm_mode = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CaseOut(BaseModel):
    id: int
    title: str
    device_model: str
    symptom: str
    solution: str
    image_path: str | None
    image_url: str | None = None
    status: str
    user_id: int | None = None
    author: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None

    if _PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:

        class Config:
            orm_mode = True


class CaseReview(BaseModel):
    approve: bool
    comment: str | None = None


class AnnotationCreate(BaseModel):
    query: str = Field(..., min_length=1, max_length=300)
    original_answer: str = Field(..., min_length=1, max_length=4000)
    corrected_answer: str | None = Field(None, max_length=4000)
    rating: int | None = Field(None, ge=1, le=5)
    source_refs: str | None = Field(None, max_length=1000)


class AnnotationOut(BaseModel):
    id: int
    message: str = "标注已保存"


class AnnotationRecord(BaseModel):
    id: int
    query: str
    original_answer: str | None = None
    corrected_answer: str | None = None
    rating: int | None = None
    source_refs: str | None = None
    status: str = "pending"
    user_id: int | None = None
    author: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None

    if _PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:

        class Config:
            orm_mode = True


class DocumentIngestResult(BaseModel):
    source: str
    chunks: int
    message: str


class GraphNode(BaseModel):
    id: int
    name: str
    entity_type: str
    description: str | None = None


class GraphEdge(BaseModel):
    id: int
    source: int
    target: int
    relation_type: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    summary: dict[str, int] = Field(default_factory=dict)

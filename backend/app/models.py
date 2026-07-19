import enum
from datetime import datetime
from pathlib import Path

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda obj: [e.value for e in obj], native_enum=False),
        default=UserRole.user,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CaseStudy(Base):
    __tablename__ = "case_studies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(256))
    device_model: Mapped[str] = mapped_column(String(128), index=True)
    symptom: Mapped[str] = mapped_column(Text)
    solution: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus, values_callable=lambda obj: [e.value for e in obj], native_enum=False),
        default=AuditStatus.pending,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def image_url(self) -> str | None:
        if not self.image_path:
            return None
        return f"/uploads/{Path(self.image_path).name}"


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query: Mapped[str] = mapped_column(Text)
    original_answer: Mapped[str] = mapped_column(Text)
    corrected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_refs: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus, values_callable=lambda obj: [e.value for e in obj], native_enum=False),
        default=AuditStatus.pending,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class KnowledgeEntity(Base):
    __tablename__ = "knowledge_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class KnowledgeRelation(Base):
    __tablename__ = "knowledge_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_entities.id"))
    target_id: Mapped[int] = mapped_column(ForeignKey("knowledge_entities.id"))
    relation_type: Mapped[str] = mapped_column(String(64))

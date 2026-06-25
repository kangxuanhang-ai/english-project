import enum
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base

# PostgreSQL 原生 enum 存小写 value；勿用 Python Enum 成员名绑定（会发 PROCESSING 导致 500）
document_status_enum = ENUM(
    "pending",
    "processing",
    "ready",
    "failed",
    name="documentstatus",
    create_type=False,
)


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_document"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer)
    minio_key: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(
        document_status_enum,
        default=DocumentStatus.PENDING.value,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(
        String(30), ForeignKey("user.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    chunks = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )
    uploader = relationship("User", foreign_keys=[uploaded_by])


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunk"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("knowledge_document.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(Vector(settings.embedding_dimensions))
    token_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    document = relationship("KnowledgeDocument", back_populates="chunks")

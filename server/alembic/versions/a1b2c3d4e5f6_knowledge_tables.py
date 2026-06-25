"""knowledge tables

Revision ID: a1b2c3d4e5f6
Revises: 8d4e2f1a6b3c
Create Date: 2026-06-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from app.config import settings

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "8d4e2f1a6b3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

document_status = postgresql.ENUM(
    "pending",
    "processing",
    "ready",
    "failed",
    name="documentstatus",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE documentstatus AS ENUM ('pending', 'processing', 'ready', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.create_table(
        "knowledge_document",
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("minio_key", sa.String(), nullable=False),
        sa.Column("status", document_status, nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "knowledge_chunk",
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("document_id", sa.String(length=30), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(settings.embedding_dimensions), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_knowledge_chunk_document_id", "knowledge_chunk", ["document_id"])
    op.execute(
        """
        CREATE INDEX idx_knowledge_chunk_embedding ON knowledge_chunk
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_knowledge_chunk_embedding")
    op.drop_index("idx_knowledge_chunk_document_id", table_name="knowledge_chunk")
    op.drop_table("knowledge_chunk")
    op.drop_table("knowledge_document")
    op.execute("DROP TYPE IF EXISTS documentstatus")

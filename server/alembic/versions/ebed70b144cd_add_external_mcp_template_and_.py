"""add external mcp template and connection tables

Revision ID: ebed70b144cd
Revises: d85e72a23457
Create Date: 2026-06-30 16:09:16.541606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "ebed70b144cd"
down_revision: Union[str, Sequence[str], None] = "d85e72a23457"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mcp_template",
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("alias", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("header_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("globally_enabled", sa.Boolean(), nullable=False),
        sa.Column("enabled_roles", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tools_cache", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exposed_tools", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fetch_url_allowlist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias"),
    )
    op.create_table(
        "user_mcp_connection",
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("user_id", sa.String(length=30), nullable=False),
        sa.Column("template_id", sa.String(length=30), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("headers_enc", sa.Text(), nullable=True),
        sa.Column("tools_cache", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["mcp_template.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "template_id"),
    )
    op.create_index(
        op.f("ix_user_mcp_connection_user_id"),
        "user_mcp_connection",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_mcp_connection_user_id"), table_name="user_mcp_connection")
    op.drop_table("user_mcp_connection")
    op.drop_table("mcp_template")

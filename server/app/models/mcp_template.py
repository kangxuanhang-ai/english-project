from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class McpTemplate(Base):
    __tablename__ = "mcp_template"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    alias: Mapped[str] = mapped_column(String(32), unique=True)
    display_name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(512))
    header_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    globally_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled_roles: Mapped[list] = mapped_column(JSONB, default=list)
    tools_cache: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    exposed_tools: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    fetch_url_allowlist: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

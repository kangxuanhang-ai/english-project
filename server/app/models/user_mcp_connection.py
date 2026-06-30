from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserMcpConnection(Base):
    __tablename__ = "user_mcp_connection"
    __table_args__ = (UniqueConstraint("user_id", "template_id"),)

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    template_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("mcp_template.id", ondelete="CASCADE")
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    headers_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools_cache: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

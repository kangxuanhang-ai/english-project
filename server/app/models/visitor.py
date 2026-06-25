from datetime import datetime

from sqlalchemy import DateTime, Float, Index, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Visitor(Base):
    __tablename__ = "visitor"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    anonymous_id: Mapped[str] = mapped_column(String, unique=True)
    user_id: Mapped[str | None] = mapped_column(
        String(30), ForeignKey("user.id", ondelete="CASCADE"), nullable=True
    )
    browser: Mapped[str | None] = mapped_column(String, nullable=True)
    os: Mapped[str | None] = mapped_column(String, nullable=True)
    device: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="visitors")
    page_views = relationship("PageView", back_populates="visitor", cascade="all, delete-orphan")
    track_events = relationship("TrackEvent", back_populates="visitor", cascade="all, delete-orphan")
    performance_entries = relationship("PerformanceEntry", back_populates="visitor", cascade="all, delete-orphan")
    error_entries = relationship("ErrorEntry", back_populates="visitor", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_visitor_user_id", "user_id"),
        Index("idx_visitor_anonymous_id", "anonymous_id"),
    )


class PageView(Base):
    __tablename__ = "page_view"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("visitor.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String)
    referrer: Mapped[str | None] = mapped_column(String, nullable=True)
    path: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    visitor = relationship("Visitor", back_populates="page_views")

    __table_args__ = (
        Index("idx_page_view_visitor_created", "visitor_id", "created_at"),
        Index("idx_page_view_path_created", "path", "created_at"),
    )


class TrackEvent(Base):
    __tablename__ = "track_event"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("visitor.id", ondelete="CASCADE"), nullable=False
    )
    event: Mapped[str] = mapped_column(String)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    visitor = relationship("Visitor", back_populates="track_events")

    __table_args__ = (
        Index("idx_track_event_visitor_created", "visitor_id", "created_at"),
        Index("idx_track_event_event_created", "event", "created_at"),
    )


class PerformanceEntry(Base):
    __tablename__ = "performance_entry"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("visitor.id", ondelete="CASCADE"), nullable=False
    )
    fp: Mapped[float | None] = mapped_column(Float, nullable=True)
    fcp: Mapped[float | None] = mapped_column(Float, nullable=True)
    lcp: Mapped[float | None] = mapped_column(Float, nullable=True)
    inp: Mapped[float | None] = mapped_column(Float, nullable=True)
    cls: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    visitor = relationship("Visitor", back_populates="performance_entries")

    __table_args__ = (
        Index("idx_performance_entry_fp_created", "fp", "created_at"),
        Index("idx_performance_entry_fcp_created", "fcp", "created_at"),
        Index("idx_performance_entry_lcp_created", "lcp", "created_at"),
        Index("idx_performance_entry_inp_created", "inp", "created_at"),
        Index("idx_performance_entry_cls_created", "cls", "created_at"),
        Index("idx_performance_entry_all_metrics", "fp", "fcp", "lcp", "inp", "cls", "created_at"),
    )


class ErrorEntry(Base):
    __tablename__ = "error_entry"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("visitor.id", ondelete="CASCADE"), nullable=False
    )
    error: Mapped[str] = mapped_column(String)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    visitor = relationship("Visitor", back_populates="error_entries")

    __table_args__ = (
        Index("idx_error_entry_visitor_created", "visitor_id", "created_at"),
        Index("idx_error_entry_error_created", "error", "created_at"),
    )

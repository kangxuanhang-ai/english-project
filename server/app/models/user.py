from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    phone: Mapped[str] = mapped_column(String, unique=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    password: Mapped[str] = mapped_column(String)
    avatar: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    is_timing_task: Mapped[bool] = mapped_column(Boolean, default=False)
    timing_task_time: Mapped[str] = mapped_column(String, default="00:00:00")
    word_number: Mapped[int] = mapped_column(Integer, default=0)
    day_number: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_check_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    role: Mapped[str] = mapped_column(String, default="user")  # user | admin

    # 关系
    word_book_records = relationship("WordBookRecord", back_populates="user", cascade="all, delete-orphan")
    payment_records = relationship("PaymentRecord", back_populates="user", cascade="all, delete-orphan")
    course_records = relationship("CourseRecord", back_populates="user", cascade="all, delete-orphan")
    visitors = relationship("Visitor", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

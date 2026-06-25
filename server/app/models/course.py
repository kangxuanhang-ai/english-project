from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Course(Base):
    __tablename__ = "course"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    course_records = relationship("CourseRecord", back_populates="course")


class CourseRecord(Base):
    __tablename__ = "course_record"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(30), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[str] = mapped_column(String(30), ForeignKey("course.id", ondelete="CASCADE"), nullable=False)
    is_purchased: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    payment_record_id: Mapped[str | None] = mapped_column(
        String(30), ForeignKey("payment_record.id", ondelete="CASCADE"), nullable=True
    )

    user = relationship("User", back_populates="course_records")
    course = relationship("Course", back_populates="course_records")
    payment_record = relationship("PaymentRecord", back_populates="course_records")

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_course_record_user_course"),
    )

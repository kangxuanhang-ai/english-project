from datetime import datetime
from decimal import Decimal
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TradeStatus(str, enum.Enum):
    NOT_PAY = "NOT_PAY"
    WAIT_BUYER_PAY = "WAIT_BUYER_PAY"
    TRADE_CLOSED = "TRADE_CLOSED"
    TRADE_SUCCESS = "TRADE_SUCCESS"
    TRADE_FINISHED = "TRADE_FINISHED"


class PaymentRecord(Base):
    __tablename__ = "payment_record"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(30), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    trade_no: Mapped[str | None] = mapped_column(String, nullable=True)
    out_trade_no: Mapped[str] = mapped_column(String, unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    trade_status: Mapped[TradeStatus] = mapped_column(
        Enum(TradeStatus), default=TradeStatus.NOT_PAY
    )
    send_pay_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="payment_records")
    course_records = relationship("CourseRecord", back_populates="payment_record")

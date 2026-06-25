from decimal import Decimal

from pydantic import BaseModel, Field


class CreatePayDto(BaseModel):
    subject: str
    body: str
    total_amount: Decimal = Field(..., description="支付金额，须与课程标价一致")
    courseId: str


class SyncPayDto(BaseModel):
    outTradeNo: str


class ResumePayDto(BaseModel):
    courseId: str

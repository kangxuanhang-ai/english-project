from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.pay import CreatePayDto
from app.services.pay import create_payment, handle_payment_notify

router = APIRouter(prefix="/api/v1/pay", tags=["pay"])


@router.post("/create")
async def create(
    data: CreatePayDto,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建支付订单。对应 NestJS POST /api/v1/pay/create（需要认证）"""
    try:
        result = await create_payment(db, data.model_dump(), user["userId"])
        return {"data": result, "code": 200, "message": "创建成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.api_route("/notify", methods=["GET", "POST"])
async def notify(request: Request, db: AsyncSession = Depends(get_db)):
    """支付宝回调。对应 NestJS ALL /api/v1/pay/notify"""
    if request.method == "POST":
        form_data = await request.form()
        data = dict(form_data)
    else:
        data = dict(request.query_params)

    success = await handle_payment_notify(db, data)
    return PlainTextResponse("success" if success else "failure")

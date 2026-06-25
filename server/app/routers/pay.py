from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.rate_limit import limiter
from app.schemas.pay import CreatePayDto, SyncPayDto, ResumePayDto
from app.services.pay import create_payment, handle_payment_notify, sync_payment_status, resume_payment

router = APIRouter(prefix="/api/v1/pay", tags=["pay"])


@limiter.limit("10/minute")
@router.post("/create")
async def create(
    request: Request,
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


@limiter.limit("30/minute")
@router.post("/sync")
async def sync(
    request: Request,
    data: SyncPayDto,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """主动同步支付状态（notify 未到达时前端轮询）"""
    try:
        result = await sync_payment_status(db, data.outTradeNo, user["userId"])
        return {"data": result, "code": 200, "message": "查询成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@limiter.limit("10/minute")
@router.post("/resume")
async def resume(
    request: Request,
    data: ResumePayDto,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """为未完成订单重新生成支付 URL"""
    try:
        result = await resume_payment(db, user["userId"], data.courseId)
        return {"data": result, "code": 200, "message": "成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/notify")
async def notify(request: Request, db: AsyncSession = Depends(get_db)):
    """支付宝异步回调（仅 POST）"""
    form_data = await request.form()
    data = dict(form_data)

    success = await handle_payment_notify(db, data)
    return PlainTextResponse("success" if success else "failure")

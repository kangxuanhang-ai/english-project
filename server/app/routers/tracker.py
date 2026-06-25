from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.rate_limit import limiter
from app.schemas.tracker import (
    UvDto,
    UpdateUvDto,
    PvDto,
    EventDto,
    PerformanceDto,
    ErrorDto,
)
from app.services.tracker import (
    upsert_visitor,
    update_visitor,
    record_pv,
    record_event,
    record_performance,
    record_error,
)

router = APIRouter(prefix="/api/v1/tracker", tags=["tracker"])

MAX_TRACKER_BODY_BYTES = 65536


async def _limit_tracker_body(request: Request) -> None:
    length = request.headers.get("content-length")
    if length and int(length) > MAX_TRACKER_BODY_BYTES:
        raise HTTPException(status_code=413, detail="请求体过大")


@router.post("/uv")
@limiter.limit("120/minute")
async def uv(
    request: Request,
    data: UvDto,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_limit_tracker_body),
):
    visitor_id = await upsert_visitor(db, data.model_dump())
    return {"data": visitor_id, "code": 200, "message": "上报成功"}


@router.post("/update-uv")
@limiter.limit("120/minute")
async def update_uv(
    request: Request,
    data: UpdateUvDto,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_limit_tracker_body),
):
    await update_visitor(db, data.model_dump())
    return {"data": True, "code": 200, "message": "更新成功"}


@router.post("/pv")
@limiter.limit("120/minute")
async def pv(
    request: Request,
    data: PvDto,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_limit_tracker_body),
):
    await record_pv(db, data.model_dump())
    return {"data": True, "code": 200, "message": "上报成功"}


@router.post("/event")
@limiter.limit("120/minute")
async def event(
    request: Request,
    data: EventDto,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_limit_tracker_body),
):
    await record_event(db, data.model_dump())
    return {"data": True, "code": 200, "message": "上报成功"}


@router.post("/performance")
@limiter.limit("120/minute")
async def performance(
    request: Request,
    data: PerformanceDto,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_limit_tracker_body),
):
    await record_performance(db, data.model_dump())
    return {"data": True, "code": 200, "message": "上报成功"}


@router.post("/error")
@limiter.limit("120/minute")
async def error(
    request: Request,
    data: ErrorDto,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_limit_tracker_body),
):
    await record_error(db, data.model_dump())
    return {"data": True, "code": 200, "message": "上报成功"}

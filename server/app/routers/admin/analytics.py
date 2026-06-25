from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.services.admin.analytics import (
    get_analytics_overview,
    get_performance,
    get_top_pages,
    list_errors,
)

router = APIRouter(prefix="/analytics", tags=["admin-analytics"])


@router.get("/overview")
async def admin_analytics_overview(
    days: int = Query(7, ge=7, le=30),
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if days not in (7, 30):
        days = 7
    data = await get_analytics_overview(db, days=days)
    return {"data": data, "code": 200, "message": "查询成功"}


@router.get("/pages")
async def admin_analytics_pages(
    days: int = Query(7, ge=7, le=30),
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if days not in (7, 30):
        days = 7
    data = await get_top_pages(db, days=days)
    return {"data": data, "code": 200, "message": "查询成功"}


@router.get("/errors")
async def admin_analytics_errors(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await list_errors(db, page=page, page_size=pageSize)
    return {"data": data, "code": 200, "message": "查询成功"}


@router.get("/performance")
async def admin_analytics_performance(
    days: int = Query(7, ge=7, le=30),
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if days not in (7, 30):
        days = 7
    data = await get_performance(db, days=days)
    return {"data": data, "code": 200, "message": "查询成功"}

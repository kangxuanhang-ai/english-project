from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.services.admin.orders import export_orders_csv, get_order_detail, list_orders

router = APIRouter(prefix="/orders", tags=["admin-orders"])


@router.get("")
async def admin_orders(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    status: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
    keyword: str | None = None,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await list_orders(
        db,
        page=page,
        page_size=pageSize,
        status=status,
        start_date=startDate,
        end_date=endDate,
        keyword=keyword,
    )
    return {"data": data, "code": 200, "message": "查询成功"}


@router.get("/export")
async def admin_export_orders(
    status: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
    keyword: str | None = None,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    csv_text = await export_orders_csv(
        db,
        status=status,
        start_date=startDate,
        end_date=endDate,
        keyword=keyword,
    )
    filename = f"orders-{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{order_id}")
async def admin_order_detail(
    order_id: str,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await get_order_detail(db, order_id)
    if not data:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {"data": data, "code": 200, "message": "查询成功"}

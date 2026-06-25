from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.services.admin.dashboard import get_admin_dashboard

router = APIRouter()


@router.get("/dashboard")
async def admin_dashboard(
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await get_admin_dashboard(db)
    return {"data": data, "code": 200, "message": "查询成功"}

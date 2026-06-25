from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.services.admin.users import get_user_detail, list_users

router = APIRouter(prefix="/users", tags=["admin-users"])


@router.get("")
async def admin_users(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    keyword: str | None = None,
    role: str | None = Query(None, pattern="^(user|admin)$"),
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await list_users(db, page=page, page_size=pageSize, keyword=keyword, role=role)
    return {"data": data, "code": 200, "message": "查询成功"}


@router.get("/{user_id}")
async def admin_user_detail(
    user_id: str,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await get_user_detail(db, user_id)
    if not data:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"data": data, "code": 200, "message": "查询成功"}

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.course import get_course_list, get_my_courses

router = APIRouter(prefix="/api/v1/course", tags=["course"])


@router.get("/list")
async def list_courses(
    page: int = Query(1, ge=1, le=1000),
    pageSize: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """课程列表（分页）。对应 NestJS GET /api/v1/course/list"""
    result = await get_course_list(db, page=page, page_size=pageSize)
    return {"data": result, "code": 200, "message": "查询成功"}


@router.get("/my")
async def my_courses(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """我的课程。对应 NestJS GET /api/v1/course/my（需要认证）"""
    result = await get_my_courses(db, user["userId"])
    return {"data": result, "code": 200, "message": "查询成功"}

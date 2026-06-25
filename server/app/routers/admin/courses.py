from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.services.admin.courses import (
    create_course,
    get_course,
    list_admin_courses,
    set_course_published,
    update_course,
    upload_course_cover,
)

router = APIRouter(prefix="/courses", tags=["admin-courses"])


class CourseBody(BaseModel):
    name: str
    value: str
    description: str | None = None
    teacher: str
    url: str
    price: Decimal = Field(ge=0)


class CourseUpdateBody(BaseModel):
    name: str | None = None
    value: str | None = None
    description: str | None = None
    teacher: str | None = None
    url: str | None = None
    price: Decimal | None = Field(default=None, ge=0)


@router.get("")
async def admin_courses(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await list_admin_courses(db, page=page, page_size=pageSize)
    return {"data": data, "code": 200, "message": "查询成功"}


@router.post("")
async def admin_create_course(
    body: CourseBody,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await create_course(db, body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"data": data, "code": 200, "message": "创建成功"}


@router.post("/upload-cover")
async def admin_upload_course_cover(
    file: UploadFile = File(...),
    _admin: dict = Depends(get_current_admin),
):
    try:
        data = await upload_course_cover(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"data": data, "code": 200, "message": "上传成功"}


@router.get("/{course_id}")
async def admin_get_course(
    course_id: str,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await get_course(db, course_id)
    if not data:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"data": data, "code": 200, "message": "查询成功"}


@router.put("/{course_id}")
async def admin_update_course(
    course_id: str,
    body: CourseUpdateBody,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await update_course(db, course_id, body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not data:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"data": data, "code": 200, "message": "更新成功"}


@router.put("/{course_id}/publish")
async def admin_publish_course(
    course_id: str,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await set_course_published(db, course_id, True)
    if not data:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"data": data, "code": 200, "message": "已上架"}


@router.put("/{course_id}/unpublish")
async def admin_unpublish_course(
    course_id: str,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await set_course_published(db, course_id, False)
    if not data:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"data": data, "code": 200, "message": "已下架"}

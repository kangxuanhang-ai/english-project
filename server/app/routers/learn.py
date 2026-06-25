from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.learn import SaveWordMasterDto
from app.services.learn import get_word_list, save_word_master

router = APIRouter(prefix="/api/v1/learn", tags=["learn"])


@router.get("/word/{course_id}")
async def word_list(course_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取课程单词。对应 NestJS GET /api/v1/learn/word/:id"""
    try:
        result = await get_word_list(db, course_id, user["userId"])
        return {"data": result, "code": 200, "message": "查询成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/word/master")
async def master(data: SaveWordMasterDto, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """标记单词掌握。对应 NestJS POST /api/v1/learn/word/master"""
    result = await save_word_master(db, data.wordIds, user["userId"])
    return {"data": result, "code": 200, "message": "保存成功"}

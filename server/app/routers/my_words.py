from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.my_words import AddWordsDto, MarkMasteredDto
from app.services.my_words import add_words, list_my_words, mark_mastered, remove_word

router = APIRouter(prefix="/api/v1/my-words", tags=["my-words"])


@router.get("")
async def get_my_words(
    status: str = Query("learning", pattern="^(learning|mastered)$"),
    page: int = Query(1, ge=1, le=1000),
    pageSize: int = Query(12, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """分页查询我的生词本。"""
    result = await list_my_words(db, user["userId"], status, page, pageSize)
    return {"data": result, "code": 200, "message": "查询成功"}


@router.post("")
async def post_add_words(
    data: AddWordsDto,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """加入生词本（复习中）。"""
    result = await add_words(db, user["userId"], data.words)
    return {"data": result, "code": 200, "message": "添加成功"}


@router.post("/master")
async def post_mark_mastered(
    data: MarkMasteredDto,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记掌握。"""
    if not data.wordIds and not data.words:
        raise HTTPException(status_code=400, detail="请提供 wordIds 或 words")
    result = await mark_mastered(
        db, user["userId"], word_ids=data.wordIds, words=data.words
    )
    return {"data": result, "code": 200, "message": "保存成功"}


@router.delete("/{word_id}")
async def delete_my_word(
    word_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从复习中移除。"""
    result = await remove_word(db, user["userId"], word_id)
    if not result.get("removed"):
        raise HTTPException(status_code=400, detail=result.get("message", "删除失败"))
    return {"data": result, "code": 200, "message": "删除成功"}

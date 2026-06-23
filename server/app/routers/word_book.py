from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.word_book import get_word_book_list

router = APIRouter(prefix="/api/v1/word-book", tags=["word-book"])


@router.get("")
async def list_words(
    page: int = Query(1, ge=1, le=1000),
    pageSize: int = Query(12, ge=1, le=100),
    word: str | None = Query(None),
    gk: str | None = Query(None),
    zk: str | None = Query(None),
    gre: str | None = Query(None),
    toefl: str | None = Query(None),
    ielts: str | None = Query(None),
    cet6: str | None = Query(None),
    cet4: str | None = Query(None),
    ky: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """分页查询单词。对应 NestJS GET /api/v1/word-book"""
    query = {
        "page": page, "pageSize": pageSize, "word": word,
        "gk": gk, "zk": zk, "gre": gre, "toefl": toefl,
        "ielts": ielts, "cet6": cet6, "cet4": cet4, "ky": ky,
    }
    result = await get_word_book_list(db, query)
    return {"data": result, "code": 200, "message": "查询成功"}

from sqlalchemy import cast, func, Integer, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.word_book import WordBook


def to_boolean(value: str | None) -> bool | None:
    """将字符串 'true' 转为布尔值，对应 NestJS 的 toBoolean"""
    if value == "true":
        return True
    return None


async def get_word_book_list(db: AsyncSession, query: dict) -> dict:
    """
    分页查询单词列表，支持标签过滤。
    对应 NestJS WordBookService.findAll。
    """
    page = query.get("page", 1)
    page_size = query.get("pageSize", 12)
    word = query.get("word")

    # 构建过滤条件
    filters = []
    if word:
        filters.append(WordBook.word.contains(word))

    # 标签过滤
    for tag in ["gk", "zk", "gre", "toefl", "ielts", "cet6", "cet4", "ky"]:
        val = to_boolean(query.get(tag))
        if val is not None:
            filters.append(getattr(WordBook, tag) == val)

    # 查询总数
    count_stmt = select(func.count()).select_from(WordBook)
    for f in filters:
        count_stmt = count_stmt.where(f)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 查询列表
    list_stmt = select(WordBook)
    for f in filters:
        list_stmt = list_stmt.where(f)
    list_stmt = list_stmt.order_by(cast(WordBook.frq, Integer).desc())
    list_stmt = list_stmt.offset((page - 1) * page_size).limit(page_size)

    list_result = await db.execute(list_stmt)
    words = list_result.scalars().all()

    # 转为响应格式
    word_list = []
    for w in words:
        word_list.append({
            "id": w.id,
            "word": w.word,
            "phonetic": w.phonetic,
            "definition": w.definition,
            "translation": w.translation,
            "pos": w.pos,
            "collins": w.collins,
            "oxford": w.oxford,
            "tag": w.tag,
            "bnc": w.bnc,
            "frq": w.frq,
            "exchange": w.exchange,
            "gk": w.gk,
            "zk": w.zk,
            "gre": w.gre,
            "toefl": w.toefl,
            "ielts": w.ielts,
            "cet6": w.cet6,
            "cet4": w.cet4,
            "ky": w.ky,
        })

    return {"total": total, "list": word_list}

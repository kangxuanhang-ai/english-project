from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.word_book import WordBook


async def lookup_words(db: AsyncSession, words: list[str]) -> list[dict]:
    """批量查词，返回词条 dict 列表（未找到的项含 error 字段）。"""
    cleaned = [w.lower().strip() for w in words if w and w.strip()]
    if not cleaned:
        return [{"error": "未提供有效单词"}]

    result = await db.execute(select(WordBook).where(WordBook.word.in_(cleaned)))
    entries = {entry.word: entry for entry in result.scalars().all()}

    results: list[dict] = []
    for word in cleaned:
        entry = entries.get(word)
        if entry:
            results.append(
                {
                    "word": entry.word,
                    "phonetic": entry.phonetic,
                    "definition": entry.definition,
                    "translation": entry.translation,
                    "pos": entry.pos,
                    "exchange": entry.exchange,
                }
            )
        else:
            results.append({"error": f"未找到单词 '{word}'"})
    return results

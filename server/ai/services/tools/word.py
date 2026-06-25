import json
from langchain_core.tools import tool
from sqlalchemy import select
from app.database import async_session
from app.models.word_book import WordBook


@tool
async def word_lookup(words: list[str]) -> str:
    """批量查询英语单词的详细信息，包括音标、中文释义、例句。
    当用户询问一个或多个单词的意思、用法、拼写时使用此工具。
    传入单词列表，返回每个单词的释义。单个单词也用列表传入。
    不要用于检查语法或搜索互联网信息。"""
    cleaned = [w.lower().strip() for w in words if w.strip()]
    if not cleaned:
        return json.dumps({"error": "未提供有效单词"}, ensure_ascii=False)

    async with async_session() as session:
        result = await session.execute(
            select(WordBook).where(WordBook.word.in_(cleaned))
        )
        entries = {entry.word: entry for entry in result.scalars().all()}

        results = []
        for word in cleaned:
            entry = entries.get(word)
            if entry:
                results.append({
                    "word": entry.word,
                    "phonetic": entry.phonetic,
                    "definition": entry.definition,
                    "translation": entry.translation,
                    "pos": entry.pos,
                    "exchange": entry.exchange,
                })
            else:
                results.append({"error": f"未找到单词 '{word}'"})

        return json.dumps(results, ensure_ascii=False)

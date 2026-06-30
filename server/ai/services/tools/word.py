import json

from langchain_core.tools import tool

from app.database import async_session
from app.services.word_lookup import lookup_words


@tool
async def word_lookup(words: list[str]) -> str:
    """批量查询英语单词的详细信息，包括音标、中文释义、例句。
    当用户询问一个或多个单词的意思、用法、拼写时使用此工具。
    传入单词列表，返回每个单词的释义。单个单词也用列表传入。
    不要用于检查语法或搜索互联网信息。"""
    async with async_session() as session:
        results = await lookup_words(session, words)
    return json.dumps(results, ensure_ascii=False)

# server/ai/services/tools/my_words.py
import json
from typing import Union

from langchain_core.tools import tool

from app.database import async_session
from app.services.my_words import add_words


def _normalize_words(words: Union[list[str], str]) -> list[str]:
    if isinstance(words, str):
        parts = [p.strip() for p in words.replace("\n", ",").split(",")]
        return [p for p in parts if p]
    return list(words)


def make_add_my_words(user_id: str):
    """返回绑定 user_id 的生词本写入工具。"""

    @tool
    async def add_my_words(words: Union[list[str], str]) -> str:
        """将英文单词加入当前用户的生词本（复习中）。
        当用户说「加入生词本」「收藏这些词」「把这些单词放进生词本」时使用。
        传入英文单词列表，或逗号分隔的单词字符串。返回 added / skipped 明细。"""
        normalized = _normalize_words(words)
        async with async_session() as db:
            result = await add_words(db, user_id, normalized)
        return json.dumps(result, ensure_ascii=False)

    return add_my_words

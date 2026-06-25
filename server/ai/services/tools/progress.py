# server/ai/services/tools/progress.py
from langchain_core.tools import tool

from ai.services.user_context import fetch_user_progress_json


def make_progress_query(user_id: str):
    """返回绑定了 user_id 的 progress_query 工具"""

    @tool
    async def progress_query() -> str:
        """查询用户的学习进度数据，包括已掌握单词数、全部已掌握单词列表、课程完成情况。
        当用户询问自己的学习进度、掌握了哪些单词、学了多少课程时使用。
        mastered_words 字段包含已掌握单词列表（按最近掌握排序，最多 500 个），请据此回答用户。"""
        return await fetch_user_progress_json(user_id)

    return progress_query

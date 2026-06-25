import json
from langchain_core.tools import tool
from ai.services.llm import create_bocha_search


@tool
async def web_search(query: str) -> str:
    """搜索互联网获取实时信息。仅在以下情况使用：
    1. 用户明确要求搜索
    2. 问题需要最新信息（如新闻、最新术语）
    3. 问题超出英语学习范畴
    查词、语法问题请优先使用 word_lookup 和 grammar_check。"""
    try:
        result = await create_bocha_search(query)
        if not result or not result.strip():
            return json.dumps({"error": "未找到相关搜索结果"}, ensure_ascii=False)
        return result[:5000]
    except Exception as e:
        return json.dumps({"error": f"搜索失败: {e}"}, ensure_ascii=False)

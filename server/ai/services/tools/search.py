import json
from langchain_core.tools import tool
from ai.services.llm import create_bocha_search


@tool
async def web_search(query: str) -> str:
    """搜索互联网获取实时信息（天气、新闻、最新政策等）。仅在以下情况使用：
    1. 用户已开启联网搜索，或问题需要最新外部信息
    2. 问题超出平台知识库范畴（如天气、新闻、股价）
    查平台内部资料用 knowledge_search；查单词/语法用 word_lookup、grammar_check。"""
    try:
        result = await create_bocha_search(query)
        if not result or not result.strip():
            return json.dumps({"error": "未找到相关搜索结果"}, ensure_ascii=False)
        return result[:5000]
    except Exception as e:
        return json.dumps({"error": f"搜索失败: {e}"}, ensure_ascii=False)

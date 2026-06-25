import json

from langchain_core.tools import tool

from app.database import async_session
from app.services.knowledge.search import search_knowledge

_MAX_CHARS = 3000


def _truncate_result(result: dict) -> dict:
    results = result.get("results") or []
    total = 0
    kept = []
    for item in results:
        content = item.get("content") or ""
        if total + len(content) > _MAX_CHARS:
            remain = _MAX_CHARS - total
            if remain > 80:
                kept.append({**item, "content": content[:remain] + "…"})
            break
        kept.append(item)
        total += len(content)
    return {**result, "results": kept, "totalTokens": sum(len(r["content"]) // 4 for r in kept)}


@tool
async def knowledge_search(query: str) -> str:
    """检索平台内部知识库（管理员上传的 txt/md/pdf/docx 文档）。
    适用于：某人是谁、名称/人物介绍、课程说明、平台规则、学习方法、教研内容等事实性问题。
    用户未明确说「查知识库」时，也应先调用本工具再回答。
    查单词用 word_lookup；仅在外部实时信息且用户已开联网搜索时用 web_search。"""
    q = (query or "").strip()
    if not q:
        return json.dumps({"error": "未提供检索关键词", "results": []}, ensure_ascii=False)

    async with async_session() as db:
        result = await search_knowledge(db, q, top_k=5)

    return json.dumps(_truncate_result(result), ensure_ascii=False)

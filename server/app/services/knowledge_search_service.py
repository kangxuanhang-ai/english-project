"""知识库检索薄封装（供 MCP 与 agent tool 复用）。"""
from sqlalchemy.ext.asyncio import AsyncSession

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


async def search_knowledge_for_query(
    db: AsyncSession, query: str, *, top_k: int = 5
) -> dict:
    q = (query or "").strip()
    if not q:
        return {"error": "未提供检索关键词", "results": [], "query": query, "totalTokens": 0}
    result = await search_knowledge(db, q, top_k=top_k)
    return _truncate_result(result)

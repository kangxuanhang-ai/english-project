from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.knowledge import DocumentStatus, KnowledgeChunk, KnowledgeDocument
from app.services.knowledge.embedding import embed_texts, estimate_tokens


async def search_knowledge(db: AsyncSession, query: str, top_k: int = 5) -> dict:
    query_vec = (await embed_texts([query]))[0]
    distance_expr = KnowledgeChunk.embedding.cosine_distance(query_vec)
    score_expr = (1 - distance_expr).label("score")

    stmt = (
        select(
            KnowledgeChunk.content,
            KnowledgeChunk.chunk_index,
            KnowledgeDocument.id.label("document_id"),
            KnowledgeDocument.title,
            score_expr,
        )
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .where(KnowledgeDocument.status == DocumentStatus.READY.value)
        .order_by(distance_expr)
        .limit(top_k)
    )
    rows = (await db.execute(stmt)).all()

    results = []
    for row in rows:
        score = float(row.score)
        if score < settings.knowledge_min_score:
            continue
        results.append(
            {
                "content": row.content,
                "title": row.title,
                "score": round(score, 4),
                "documentId": row.document_id,
                "chunkIndex": row.chunk_index,
            }
        )

    total_tokens = sum(estimate_tokens(r["content"]) for r in results)
    return {"results": results, "query": query, "totalTokens": total_tokens}

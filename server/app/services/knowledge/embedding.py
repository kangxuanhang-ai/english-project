import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_local_embedder = None


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _get_local_embedder():
    global _local_embedder
    if _local_embedder is None:
        from fastembed import TextEmbedding

        _local_embedder = TextEmbedding(model_name=settings.local_embedding_model)
        logger.info("本地 Embedding 模型已加载: %s", settings.local_embedding_model)
    return _local_embedder


def _embed_local(texts: list[str]) -> list[list[float]]:
    model = _get_local_embedder()
    return [vec.tolist() for vec in model.embed(texts)]


async def _embed_api(texts: list[str]) -> list[list[float]]:
    url = f"{settings.embedding_api_base.rstrip('/')}/embeddings"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={"model": settings.deepseek_embedding_model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [item["embedding"] for item in data]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if settings.embedding_mode == "api":
        vectors = await _embed_api(texts)
    else:
        import asyncio

        vectors = await asyncio.to_thread(_embed_local, texts)

    for vec in vectors:
        if len(vec) != settings.embedding_dimensions:
            raise ValueError("Embedding 维度不匹配")
    return vectors

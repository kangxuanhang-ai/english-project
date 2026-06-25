"""Phase 0: 实测 Embedding 返回维度。

DeepSeek 官方 chat API 目前可能不提供 /v1/embeddings（会 404）。
若 404，请在 spec 中改用其他 Embedding 提供商，或暂时保留 EMBEDDING_DIMENSIONS 默认值。

运行: cd server && uv run python scripts/probe_embedding.py
"""
import asyncio
import httpx
from app.config import settings

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.deepseek.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={"model": settings.deepseek_embedding_model, "input": "hello"},
        )
        resp.raise_for_status()
        vec = resp.json()["data"][0]["embedding"]
        print(f"model={settings.deepseek_embedding_model}")
        print(f"dimensions={len(vec)}")
        print(f"Set EMBEDDING_DIMENSIONS={len(vec)} in server/.env")

if __name__ == "__main__":
    asyncio.run(main())

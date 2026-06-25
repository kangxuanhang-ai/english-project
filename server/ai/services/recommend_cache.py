"""推荐结果缓存 — 默认进程内；配置 REDIS_URL 时使用 Redis（多 worker 共享）。"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

from ai.config import ai_settings

logger = logging.getLogger(__name__)

_memory_cache: dict[str, dict[str, Any]] = {}
_redis_client = None


def _cache_key(user_id: str) -> str:
    return f"en:recommend:{user_id}"


async def _get_redis():
    global _redis_client
    if not ai_settings.redis_url:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis.asyncio as aioredis

        _redis_client = aioredis.from_url(
            ai_settings.redis_url, decode_responses=True
        )
        return _redis_client
    except Exception as e:
        logger.warning("Redis 不可用，推荐缓存回退内存: %s", e)
        return None


async def get_cached_recommendation(user_id: str) -> dict | None:
    """读取缓存条目 {data, timestamp, ttl} 或 None。"""
    redis = await _get_redis()
    if redis:
        try:
            raw = await redis.get(_cache_key(user_id))
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning("Redis cache get failed: %s", e)

    return _memory_cache.get(user_id)


async def set_cached_recommendation(
    user_id: str, data: dict, ttl: int
) -> None:
    entry = {
        "data": data,
        "timestamp": datetime.now(timezone.utc).timestamp(),
        "ttl": ttl,
    }
    redis = await _get_redis()
    if redis:
        try:
            await redis.set(_cache_key(user_id), json.dumps(entry), ex=ttl)
            return
        except Exception as e:
            logger.warning("Redis cache set failed: %s", e)

    _memory_cache[user_id] = entry


async def delete_cached_recommendation(user_id: str) -> None:
    redis = await _get_redis()
    if redis:
        try:
            await redis.delete(_cache_key(user_id))
        except Exception as e:
            logger.warning("Redis cache delete failed: %s", e)
    _memory_cache.pop(user_id, None)


async def close_recommend_cache() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None

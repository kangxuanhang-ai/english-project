"""当前对话内的课程推荐缓存 — 默认进程内；配置 REDIS_URL 时使用 Redis。"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

from ai.config import ai_settings

logger = logging.getLogger(__name__)

CONV_RECOMMEND_TTL = 24 * 60 * 60
_memory_cache: dict[str, dict[str, Any]] = {}
_redis_client = None


def _cache_key(conversation_id: str) -> str:
    return f"en:conv_recommend:{conversation_id}"


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
        logger.warning("Redis 不可用，对话推荐缓存回退内存: %s", e)
        return None


async def get_cached_conversation_recommend(conversation_id: str) -> dict | None:
    """读取推荐块 {courses, daily_plan?, summary?} 或 None。"""
    redis = await _get_redis()
    if redis:
        try:
            raw = await redis.get(_cache_key(conversation_id))
            if raw:
                entry = json.loads(raw)
                return entry.get("data")
        except Exception as e:
            logger.warning("Redis conv recommend get failed: %s", e)

    entry = _memory_cache.get(conversation_id)
    if entry:
        return entry.get("data")
    return None


async def set_cached_conversation_recommend(
    conversation_id: str, data: dict, ttl: int = CONV_RECOMMEND_TTL
) -> None:
    entry = {
        "data": data,
        "timestamp": datetime.now(timezone.utc).timestamp(),
        "ttl": ttl,
    }
    redis = await _get_redis()
    if redis:
        try:
            await redis.set(
                _cache_key(conversation_id), json.dumps(entry), ex=ttl
            )
            return
        except Exception as e:
            logger.warning("Redis conv recommend set failed: %s", e)

    _memory_cache[conversation_id] = entry


async def load_recommend_from_history(conversation_id: str) -> dict | None:
    """缓存 miss 时从 LangGraph 线程扫描最近一条推荐工具输出。"""
    from ai.services.chat import get_checkpointer, _extract_recommend_block

    try:
        checkpointer = await get_checkpointer()
        state = await checkpointer.aget(
            {"configurable": {"thread_id": conversation_id}}
        )
        if not state:
            return None
        messages = state.get("channel_values", {}).get("messages") or []
        for msg in reversed(messages):
            if getattr(msg, "type", "") != "tool":
                continue
            if getattr(msg, "name", "") != "course_recommendation":
                continue
            block = _extract_recommend_block(msg.content or "")
            if block and block.get("courses"):
                return block
    except Exception as e:
        logger.warning("load_recommend_from_history failed: %s", e)
    return None


async def get_conversation_recommend(conversation_id: str) -> dict | None:
    """当前对话推荐：缓存 → 历史 fallback → 回填缓存。"""
    cached = await get_cached_conversation_recommend(conversation_id)
    if cached and cached.get("courses"):
        return cached
    block = await load_recommend_from_history(conversation_id)
    if block:
        await set_cached_conversation_recommend(conversation_id, block)
        return block
    return None

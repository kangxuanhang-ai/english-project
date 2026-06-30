"""HTTP MCP API Key 鉴权中间件（ASGI）。"""
import asyncio
import hashlib
import logging

from app.services.mcp_api_key import KEY_PREFIX, resolve_user_by_key, touch_last_used
from english_mcp import db as mcp_db
from english_mcp.context import (
    AuthenticatedMcpUser,
    set_client_ip,
    set_invalid_key_header,
    set_mcp_user,
)

logger = logging.getLogger(__name__)

_HEADER_NAME = b"english-mcp-api-key"


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _extract_header(scope: dict, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("utf-8").strip()
    return None


def _extract_client_ip(scope: dict) -> str:
    forwarded = _extract_header(scope, b"x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = scope.get("client")
    if client:
        return client[0]
    return "unknown"


async def _touch_last_used_async(key_hash: str) -> None:
    if mcp_db.async_session is None:
        return
    try:
        async with mcp_db.async_session() as session:
            await touch_last_used(session, key_hash)
    except Exception as exc:
        logger.warning("更新 MCP Key last_used_at 失败: %s", exc)


def _extract_api_key(scope: dict) -> str | None:
    raw = _extract_header(scope, _HEADER_NAME)
    if raw:
        return raw

    auth = _extract_header(scope, b"authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


class McpApiKeyMiddleware:
    """解析 ENGLISH-MCP-API-KEY Header 并写入 ContextVar。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        if scope["type"] == "http":
            set_mcp_user(None)
            set_invalid_key_header(False)
            set_client_ip(_extract_client_ip(scope))

            raw_key = _extract_api_key(scope)
            if raw_key:
                if not raw_key.startswith(KEY_PREFIX):
                    set_invalid_key_header(True)
                elif mcp_db.async_session is None:
                    logger.error("MCP 数据库未初始化，无法校验 API Key")
                else:
                    async with mcp_db.async_session() as session:
                        user_id = await resolve_user_by_key(session, raw_key)
                    if user_id:
                        key_hash = _hash_key(raw_key)
                        user = AuthenticatedMcpUser(
                            user_id=user_id,
                            key_prefix=raw_key[:24],
                            key_hash=key_hash,
                        )
                        set_mcp_user(user)
                        scope["english_mcp_user"] = user
                        asyncio.create_task(_touch_last_used_async(key_hash))
                    else:
                        set_invalid_key_header(True)
                        scope["english_mcp_invalid_key"] = True

        await self.app(scope, receive, send)

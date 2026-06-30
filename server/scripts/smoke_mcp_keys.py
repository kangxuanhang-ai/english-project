"""MCP API Key 鉴权冒烟（handler 层 + HTTP 模式）。"""
import asyncio
import json
import os

os.environ["ENGLISH_MCP_HTTP"] = "1"

from app.database import async_session
from app.services.mcp_api_key import create_key, resolve_user_by_key, revoke_key
from english_mcp import db as mcp_db
from english_mcp.config import mcp_settings
from english_mcp.context import AuthenticatedMcpUser, set_mcp_user
from english_mcp.tools_handlers import run_get_learning_progress
from sqlalchemy import select
from app.models.user import User


async def main() -> None:
    mcp_db.init_db(
        mcp_settings.database_url,
        pool_size=mcp_settings.mcp_db_pool_size,
        max_overflow=mcp_settings.mcp_db_max_overflow,
    )
    try:
        async with async_session() as db:
            user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
            if not user:
                print("SKIP: no users")
                return

            created = await create_key(
                db, user.id, "smoke", "http://127.0.0.1:3002/mcp"
            )
            raw_key = created["key"]
            print("created key:", created["keyPrefix"])

        # HTTP 模式无 Key
        set_mcp_user(None)
        no_key = json.loads(await run_get_learning_progress())
        assert "error" in no_key, no_key
        print("no key error:", no_key["error"][:40])

        # 无效 Key 标记由 middleware 设置；handler 层模拟有效用户
        async with async_session() as db:
            uid = await resolve_user_by_key(db, raw_key)
            assert uid == user.id

        set_mcp_user(
            AuthenticatedMcpUser(
                user_id=user.id,
                key_prefix=raw_key[:24],
                key_hash=__import__("hashlib").sha256(raw_key.encode()).hexdigest(),
            )
        )
        with_key = json.loads(await run_get_learning_progress())
        assert "error" not in with_key, with_key
        print("progress word_count:", with_key.get("word_count"))

        async with async_session() as db:
            await revoke_key(db, user.id, created["id"])
            assert await resolve_user_by_key(db, raw_key) is None
        print("revoked ok")

        print("OK")
    finally:
        await mcp_db.dispose_db()


if __name__ == "__main__":
    asyncio.run(main())

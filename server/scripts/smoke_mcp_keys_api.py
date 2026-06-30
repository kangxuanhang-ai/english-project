"""Phase A 冒烟：MCP API Key service（需本地 DB）。"""
import asyncio

from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.user import User
from app.services.mcp_api_key import (
    MAX_KEYS_PER_USER,
    create_key,
    list_keys,
    resolve_user_by_key,
    revoke_key,
)


async def main() -> None:
    async with async_session() as db:
        user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
        if not user:
            print("SKIP: no users in database")
            return
        uid = user.id
        public_url = settings.mcp_public_url
        print(f"user: {uid}")

        created = await create_key(db, uid, "smoke-test", public_url)
        assert created["key"].startswith("en_mcp_live_")
        headers = created["claudeConfig"]["mcpServers"]["english"]["headers"]
        assert headers["ENGLISH-MCP-API-KEY"] == created["key"]
        key_id = created["id"]
        raw_key = created["key"]
        print("create_key:", created["keyPrefix"])

        keys = await list_keys(db, uid)
        assert any(k["id"] == key_id for k in keys)
        print("list_keys:", len(keys))

        resolved = await resolve_user_by_key(db, raw_key)
        assert resolved == uid
        print("resolve_user_by_key: ok")

        assert await revoke_key(db, uid, key_id) is True
        print("revoke_key: True")

        assert await resolve_user_by_key(db, raw_key) is None
        print("resolve after revoke: None")

        existing = await list_keys(db, uid)
        created_ids: list[str] = []
        for i in range(MAX_KEYS_PER_USER - len(existing)):
            r = await create_key(db, uid, f"limit-test-{i}", public_url)
            created_ids.append(r["id"])
        assert len(await list_keys(db, uid)) == MAX_KEYS_PER_USER
        print(f"active keys: {MAX_KEYS_PER_USER}")

        try:
            await create_key(db, uid, "should-fail", public_url)
            raise AssertionError("expected ValueError for max keys")
        except ValueError as e:
            assert str(e) == f"每用户最多 {MAX_KEYS_PER_USER} 个未吊销 Key"
            print("max keys limit: ok")

        for kid in created_ids:
            await revoke_key(db, uid, kid)

        print("OK")


if __name__ == "__main__":
    asyncio.run(main())

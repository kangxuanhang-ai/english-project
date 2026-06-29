#!/usr/bin/env python3
"""列出数据库用户 ID，供配置 AGENT_EVAL_USER_ID。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import async_session
from app.models.user import User


async def main() -> int:
    async with async_session() as session:
        result = await session.execute(
            select(User.id, User.name, User.phone, User.email).limit(20)
        )
        rows = result.all()
    if not rows:
        print("数据库里没有用户。请先在前端注册/登录一个账号。")
        return 1
    print("复制下面任意一行的 id 到 server/.env 的 AGENT_EVAL_USER_ID=\n")
    print(f"{'id':<32} {'name':<16} phone")
    print("-" * 70)
    for uid, name, phone, email in rows:
        print(f"{uid:<32} {name or '-':<16} {phone or '-'}")
    print("\n示例: AGENT_EVAL_USER_ID=" + rows[0][0])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

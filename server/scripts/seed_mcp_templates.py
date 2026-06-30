"""Seed 外部 MCP 模板（仅 fetch）。"""
from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from nanoid import generate
from sqlalchemy import delete, select

from app.database import async_session
from app.models.mcp_template import McpTemplate

# 已废弃模板（sidecar 未实现，seed 时清理）
REMOVED_ALIASES = ("wikipedia", "youtube")

DEFAULT_FETCH_ALLOWLIST = [
    "bbc.com",
    "bbc.co.uk",
    "wikipedia.org",
    "medium.com",
    "nationalgeographic.com",
    "youtube.com",
    "youtu.be",
    "example.com",
    "example.org",
]

TEMPLATES = [
    {
        "alias": "fetch",
        "display_name": "读网页 Fetch",
        "description": "抓取允许列表内的英文网页正文，适合阅读 BBC、维基等文章后查词讲解。",
        "url": "http://fetch-mcp:8080/mcp",
        "header_schema": {"fields": []},
        "fetch_url_allowlist": DEFAULT_FETCH_ALLOWLIST,
        "sort_order": 1,
    },
]


async def seed_mcp_templates() -> None:
    async with async_session() as db:
        await db.execute(delete(McpTemplate).where(McpTemplate.alias.in_(REMOVED_ALIASES)))
        for item in TEMPLATES:
            result = await db.execute(select(McpTemplate).where(McpTemplate.alias == item["alias"]))
            existing = result.scalar_one_or_none()
            if existing:
                continue
            db.add(
                McpTemplate(
                    id=generate(size=20),
                    alias=item["alias"],
                    display_name=item["display_name"],
                    description=item["description"],
                    url=item["url"],
                    header_schema=item["header_schema"],
                    globally_enabled=False,
                    enabled_roles=["normal"],
                    fetch_url_allowlist=item.get("fetch_url_allowlist"),
                    sort_order=item["sort_order"],
                )
            )
        await db.commit()
    print("MCP templates seeded (fetch only; removed wikipedia/youtube if present).")


def main() -> None:
    asyncio.run(seed_mcp_templates())


if __name__ == "__main__":
    main()

"""P0 spike：从 Streamable HTTP MCP 端点 list_tools。"""
from __future__ import annotations

import argparse
import asyncio
import sys

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main(url: str) -> None:
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            for tool in result.tools:
                print(tool.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", default="http://fetch-mcp:8080/mcp", nargs="?")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.url))
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

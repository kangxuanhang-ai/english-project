"""Fetch MCP Streamable HTTP 入口（Compose 内网 fetch-mcp:8080/mcp）。"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import uvicorn

from external_mcp.fetch_server import FETCH_MCP_HOST, FETCH_MCP_PORT, mcp


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    host = os.environ.get("FETCH_MCP_HOST", FETCH_MCP_HOST)
    port = int(os.environ.get("FETCH_MCP_PORT", str(FETCH_MCP_PORT)))
    app = mcp.streamable_http_app()
    logging.getLogger(__name__).info("Starting fetch MCP HTTP on %s:%s/mcp", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

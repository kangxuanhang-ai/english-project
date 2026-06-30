"""English MCP Streamable HTTP 入口（可选，默认端口 3002）。"""
import asyncio
import logging
import os
import sys


def main() -> None:
    os.environ["ENGLISH_MCP_HTTP"] = "1"

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    from english_mcp.config import mcp_settings
    from english_mcp.server import mcp

    logger = logging.getLogger(__name__)
    host = mcp_settings.mcp_http_host
    port = mcp_settings.mcp_http_port
    logger.info("Starting english_mcp HTTP on %s:%s/mcp", host, port)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()

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

    import uvicorn

    from english_mcp.config import mcp_settings
    from english_mcp import db as mcp_db
    from english_mcp.middleware import McpApiKeyMiddleware
    from english_mcp.server import mcp

    mcp_db.init_db(
        mcp_settings.database_url,
        pool_size=mcp_settings.mcp_db_pool_size,
        max_overflow=mcp_settings.mcp_db_max_overflow,
    )
    logger = logging.getLogger(__name__)
    host = mcp_settings.mcp_http_host
    port = mcp_settings.mcp_http_port
    inner = mcp.streamable_http_app()
    app = McpApiKeyMiddleware(inner)
    logger.info("Starting english_mcp HTTP on %s:%s/mcp", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

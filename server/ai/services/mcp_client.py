"""MCP HTTP Client — list_tools / call_tool（官方 SDK Streamable HTTP）。"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

logger = logging.getLogger(__name__)

MCP_TIMEOUT = 30.0


def _tool_to_dict(tool: Any) -> dict[str, Any]:
    schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {}
    return {
        "name": tool.name,
        "description": tool.description or "",
        "inputSchema": schema,
    }


def _extract_call_result(result: Any) -> str:
    if result.isError:
        parts = []
        for block in result.content or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return '{"error": "' + "; ".join(parts or ["外部服务错误"]).replace('"', '\\"') + '"}'
    parts = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts) if parts else ""


async def list_tools(url: str, headers: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """调用 MCP list_tools，返回 tool dict 列表。"""
    client_headers = headers or {}
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT, headers=client_headers) as http_client:
        async with streamable_http_client(url, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return [_tool_to_dict(tool) for tool in result.tools]


async def call_tool(
    url: str,
    name: str,
    arguments: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> str:
    """调用 MCP call_tool，返回文本结果。"""
    client_headers = headers or {}
    try:
        async with httpx.AsyncClient(timeout=MCP_TIMEOUT, headers=client_headers) as http_client:
            async with streamable_http_client(url, http_client=http_client) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
                    return _extract_call_result(result)
    except httpx.TimeoutException:
        logger.warning("MCP call_tool timeout: %s %s", url, name)
        return '{"error": "外部服务超时，请稍后重试"}'
    except Exception as exc:
        logger.warning("MCP call_tool failed: %s %s %s", url, name, exc)
        return f'{{"error": "外部服务异常: {exc}"}}'

"""从 DB 加载用户已启用的外部 MCP LangChain 工具。"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import Field, create_model
from sqlalchemy import select

from ai.services.mcp_client import call_tool
from ai.services.mcp_url_guard import validate_fetch_url, normalize_fetch_url
from app.database import async_session
from app.models.mcp_template import McpTemplate
from app.models.user_mcp_connection import UserMcpConnection
from app.services.mcp_template import resolve_exposed_tools, template_requires_user_test
from shared.mcp_crypto import decrypt_headers

logger = logging.getLogger(__name__)


def _build_args_schema(input_schema: dict | None):
    properties = (input_schema or {}).get("properties") or {}
    if not properties:
        return None
    fields: dict[str, Any] = {}
    required = set((input_schema or {}).get("required") or [])
    for key, spec in properties.items():
        py_type: Any = str
        if spec.get("type") == "integer":
            py_type = int
        elif spec.get("type") == "number":
            py_type = float
        elif spec.get("type") == "boolean":
            py_type = bool
        if key in required:
            fields[key] = (py_type, Field(..., description=spec.get("description") or ""))
        else:
            default = spec.get("default")
            fields[key] = (
                py_type | None,
                Field(default=default, description=spec.get("description") or ""),
            )
    return create_model("ExternalMcpArgs", **fields)


def _pick_tools_cache(template: McpTemplate, connection: UserMcpConnection) -> list[dict] | None:
    needs_user = template_requires_user_test(template.header_schema, connection.headers_enc)
    if needs_user:
        return connection.tools_cache
    return connection.tools_cache or template.tools_cache


def _wrap_remote_tool(
    *,
    alias: str,
    template: McpTemplate,
    remote_name: str,
    description: str,
    input_schema: dict | None,
    url: str,
    headers: dict[str, str],
) -> StructuredTool:
    prefixed = f"{alias}__{remote_name}"
    args_schema = _build_args_schema(input_schema)

    async def _handler(**kwargs: Any) -> str:
        if alias == "fetch" and "url" in kwargs and kwargs["url"]:
            allowlist = tuple(template.fetch_url_allowlist or [])
            clean_url = normalize_fetch_url(str(kwargs["url"]))
            kwargs = {**kwargs, "url": clean_url}
            try:
                validate_fetch_url(clean_url, allowlist=allowlist or None)
            except ValueError as exc:
                return f'{{"error": "{exc}"}}'
        return await call_tool(url, remote_name, kwargs, headers=headers or None)

    return StructuredTool(
        name=prefixed,
        description=description or f"外部 MCP 工具 {remote_name}",
        coroutine=_handler,
        args_schema=args_schema,
    )


async def load_external_mcp_tools(user_id: str) -> list[StructuredTool]:
    """加载用户已启用且可用的外部 MCP 工具（仅 normal 聊天调用）。"""
    async with async_session() as db:
        result = await db.execute(
            select(McpTemplate, UserMcpConnection)
            .join(UserMcpConnection, UserMcpConnection.template_id == McpTemplate.id)
            .where(
                UserMcpConnection.user_id == user_id,
                UserMcpConnection.enabled.is_(True),
                McpTemplate.globally_enabled.is_(True),
            )
            .order_by(McpTemplate.sort_order)
        )
        rows = result.all()

    tools: list[StructuredTool] = []
    for template, connection in rows:
        roles = template.enabled_roles or ["normal"]
        if "normal" not in roles:
            continue

        cache = _pick_tools_cache(template, connection)
        if not cache:
            logger.debug("skip external mcp %s: no tools cache", template.alias)
            continue

        headers: dict[str, str] = {}
        if connection.headers_enc:
            try:
                headers = decrypt_headers(connection.headers_enc)
            except Exception:
                logger.warning("decrypt headers failed for user %s template %s", user_id, template.alias)
                continue

        exposed = set(resolve_exposed_tools(template))
        for item in cache:
            name = item.get("name")
            if not name or name not in exposed:
                continue
            desc = item.get("description") or ""
            if template.alias == "fetch":
                desc += (
                    " 当用户提供 http/https 链接时必须调用本工具抓取正文；"
                    "禁止声称无法访问网页。返回正文后请继续用 word_lookup 解释难词。"
                )
            tools.append(
                _wrap_remote_tool(
                    alias=template.alias,
                    template=template,
                    remote_name=name,
                    description=desc,
                    input_schema=item.get("inputSchema"),
                    url=template.url,
                    headers=headers,
                )
            )
    return tools

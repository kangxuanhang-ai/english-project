"""用户外部 MCP 连接。"""
from __future__ import annotations

from datetime import datetime, timezone

from nanoid import generate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.services.mcp_client import list_tools
from app.models.mcp_template import McpTemplate
from app.models.user_mcp_connection import UserMcpConnection
from app.services.mcp_template import resolve_exposed_tools, template_requires_user_test
from shared.mcp_crypto import decrypt_headers, encrypt_headers


def _header_schema_fields(header_schema: dict | None) -> list[dict]:
    return (header_schema or {}).get("fields") or []


def _configured_headers(headers: dict[str, str]) -> dict[str, bool]:
    return {key: bool(value) for key, value in headers.items()}


def _mask_headers_for_response(
    header_schema: dict | None,
    headers_enc: str | None,
) -> dict[str, bool]:
    fields = _header_schema_fields(header_schema)
    if not fields:
        return {}
    configured: dict[str, bool] = {}
    stored: dict[str, str] = {}
    if headers_enc:
        try:
            stored = decrypt_headers(headers_enc)
        except Exception:
            stored = {}
    for field in fields:
        key = field.get("key", "")
        configured[key] = bool(stored.get(key))
    return configured


def _connection_tools(template: McpTemplate, connection: UserMcpConnection | None) -> list[dict]:
    if connection and connection.tools_cache:
        return connection.tools_cache
    return template.tools_cache or []


def _item_to_dict(template: McpTemplate, connection: UserMcpConnection | None) -> dict:
    tools = _connection_tools(template, connection)
    exposed = resolve_exposed_tools(template)
    tool_names = [name for name in exposed if any(t.get("name") == name for t in tools)]
    return {
        "alias": template.alias,
        "displayName": template.display_name,
        "description": template.description,
        "globallyEnabled": template.globally_enabled,
        "headerSchema": template.header_schema or {"fields": []},
        "exposedToolNames": exposed,
        "connection": {
            "enabled": bool(connection and connection.enabled),
            "configuredHeaders": _mask_headers_for_response(
                template.header_schema, connection.headers_enc if connection else None
            ),
            "lastTestedAt": connection.last_tested_at.isoformat()
            if connection and connection.last_tested_at
            else None,
            "toolNames": tool_names,
            "needsTest": template_requires_user_test(
                template.header_schema, connection.headers_enc if connection else None
            )
            and not (connection and connection.tools_cache),
        },
    }


async def list_available_for_user(db: AsyncSession, user_id: str) -> list[dict]:
    templates_result = await db.execute(
        select(McpTemplate).where(McpTemplate.globally_enabled.is_(True)).order_by(McpTemplate.sort_order)
    )
    templates = templates_result.scalars().all()
    if not templates:
        return []

    conn_result = await db.execute(
        select(UserMcpConnection).where(UserMcpConnection.user_id == user_id)
    )
    connections = {row.template_id: row for row in conn_result.scalars().all()}
    return [_item_to_dict(t, connections.get(t.id)) for t in templates]


async def upsert_connection(
    db: AsyncSession,
    user_id: str,
    alias: str,
    enabled: bool,
    headers: dict[str, str],
) -> dict:
    template = await db.execute(select(McpTemplate).where(McpTemplate.alias == alias))
    template_row = template.scalar_one_or_none()
    if not template_row:
        raise ValueError("模板不存在")
    if not template_row.globally_enabled:
        raise ValueError("管理员未开放此 MCP")

    result = await db.execute(
        select(UserMcpConnection).where(
            UserMcpConnection.user_id == user_id,
            UserMcpConnection.template_id == template_row.id,
        )
    )
    connection = result.scalar_one_or_none()

    headers_enc = encrypt_headers(headers) if headers else None
    if connection:
        connection.enabled = enabled
        connection.headers_enc = headers_enc
        if headers:
            connection.tools_cache = None
    else:
        connection = UserMcpConnection(
            id=generate(size=20),
            user_id=user_id,
            template_id=template_row.id,
            enabled=enabled,
            headers_enc=headers_enc,
        )
        db.add(connection)

    await db.commit()
    await db.refresh(connection)
    return _item_to_dict(template_row, connection)


async def test_user_connection(db: AsyncSession, user_id: str, alias: str) -> dict:
    template_result = await db.execute(select(McpTemplate).where(McpTemplate.alias == alias))
    template = template_result.scalar_one_or_none()
    if not template:
        raise ValueError("模板不存在")
    if not template.globally_enabled:
        raise ValueError("管理员未开放此 MCP")

    conn_result = await db.execute(
        select(UserMcpConnection).where(
            UserMcpConnection.user_id == user_id,
            UserMcpConnection.template_id == template.id,
        )
    )
    connection = conn_result.scalar_one_or_none()
    if not connection:
        raise ValueError("请先保存连接配置")

    headers: dict[str, str] = {}
    if connection.headers_enc:
        headers = decrypt_headers(connection.headers_enc)

    tools = await list_tools(template.url, headers=headers or None)
    connection.tools_cache = tools
    connection.last_tested_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(connection)
    return {
        "tools": tools,
        "item": _item_to_dict(template, connection),
    }


async def delete_connection(db: AsyncSession, user_id: str, alias: str) -> bool:
    template_result = await db.execute(select(McpTemplate).where(McpTemplate.alias == alias))
    template = template_result.scalar_one_or_none()
    if not template:
        return False

    conn_result = await db.execute(
        select(UserMcpConnection).where(
            UserMcpConnection.user_id == user_id,
            UserMcpConnection.template_id == template.id,
        )
    )
    connection = conn_result.scalar_one_or_none()
    if not connection:
        return False

    connection.enabled = False
    connection.headers_enc = None
    connection.tools_cache = None
    connection.last_tested_at = None
    await db.commit()
    return True

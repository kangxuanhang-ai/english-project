"""Admin MCP 模板 CRUD 与测试连接。"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.services.mcp_client import list_tools
from app.models.mcp_template import McpTemplate
from app.schemas.mcp_templates import ALLOWED_MCP_HOSTS, UpdateMcpTemplateDto


def _validate_mcp_url(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_MCP_HOSTS:
        raise ValueError(f"URL 主机须在白名单内: {', '.join(ALLOWED_MCP_HOSTS)}")


def resolve_exposed_tools(template: McpTemplate) -> list[str]:
    if template.exposed_tools:
        return list(template.exposed_tools)
    cache = template.tools_cache or []
    names = sorted(str(item.get("name", "")) for item in cache if item.get("name"))
    return names[:3]


def template_to_dict(template: McpTemplate) -> dict:
    return {
        "id": template.id,
        "alias": template.alias,
        "displayName": template.display_name,
        "description": template.description,
        "url": template.url,
        "headerSchema": template.header_schema or {"fields": []},
        "globallyEnabled": template.globally_enabled,
        "enabledRoles": template.enabled_roles or ["normal"],
        "toolsCache": template.tools_cache,
        "exposedTools": template.exposed_tools,
        "exposedToolNames": resolve_exposed_tools(template),
        "fetchUrlAllowlist": template.fetch_url_allowlist,
        "lastSyncedAt": template.last_synced_at.isoformat() if template.last_synced_at else None,
        "sortOrder": template.sort_order,
        "createdAt": template.created_at.isoformat() if template.created_at else None,
        "updatedAt": template.updated_at.isoformat() if template.updated_at else None,
    }


async def list_templates(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(McpTemplate).order_by(McpTemplate.sort_order, McpTemplate.alias))
    return [template_to_dict(row) for row in result.scalars().all()]


async def get_template(db: AsyncSession, template_id: str) -> McpTemplate | None:
    result = await db.execute(select(McpTemplate).where(McpTemplate.id == template_id))
    return result.scalar_one_or_none()


async def get_template_by_alias(db: AsyncSession, alias: str) -> McpTemplate | None:
    result = await db.execute(select(McpTemplate).where(McpTemplate.alias == alias))
    return result.scalar_one_or_none()


async def update_template(
    db: AsyncSession,
    template_id: str,
    data: UpdateMcpTemplateDto,
) -> dict:
    template = await get_template(db, template_id)
    if not template:
        raise ValueError("模板不存在")

    payload = data.model_dump(exclude_unset=True)
    if "url" in payload and payload["url"] is not None:
        _validate_mcp_url(payload["url"])
        template.url = payload["url"]
    if "description" in payload and payload["description"] is not None:
        template.description = payload["description"]
    if "globallyEnabled" in payload and payload["globallyEnabled"] is not None:
        template.globally_enabled = payload["globallyEnabled"]
    if "headerSchema" in payload and payload["headerSchema"] is not None:
        template.header_schema = payload["headerSchema"]
    if "exposedTools" in payload:
        template.exposed_tools = payload["exposedTools"]
    if "fetchUrlAllowlist" in payload and template.alias == "fetch":
        template.fetch_url_allowlist = payload["fetchUrlAllowlist"]

    await db.commit()
    await db.refresh(template)
    return template_to_dict(template)


async def test_template_connection(db: AsyncSession, template_id: str) -> dict:
    template = await get_template(db, template_id)
    if not template:
        raise ValueError("模板不存在")

    tools = await list_tools(template.url)
    template.tools_cache = tools
    template.last_synced_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(template)
    return {
        "tools": tools,
        "template": template_to_dict(template),
    }


def template_requires_user_test(header_schema: dict | None, headers_enc: str | None) -> bool:
    fields = (header_schema or {}).get("fields") or []
    if any(field.get("required") for field in fields):
        return True
    return bool(headers_enc)

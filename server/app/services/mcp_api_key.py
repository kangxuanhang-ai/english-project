import hashlib
import secrets
from datetime import datetime, timezone

from nanoid import generate
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp_api_key import McpApiKey

KEY_PREFIX = "en_mcp_live_"
MAX_KEYS_PER_USER = 3


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_raw_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def build_claude_config(raw_key: str, public_url: str) -> dict:
    """拼装 Claude Code ~/.claude.json 中的 MCP HTTP 配置片段。"""
    return {
        "mcpServers": {
            "english": {
                "type": "http",
                "url": public_url,
                "headers": {
                    "english-mcp-api-key": raw_key,
                },
                "timeout": 60000,
            }
        }
    }


def _key_to_item(record: McpApiKey) -> dict:
    """列表项：不含 hash 与明文 key。"""
    return {
        "id": record.id,
        "keyPrefix": record.key_prefix,
        "name": record.name,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
        "lastUsedAt": record.last_used_at.isoformat() if record.last_used_at else None,
    }


async def create_key(
    db: AsyncSession,
    user_id: str,
    name: str,
    public_url: str,
) -> dict:
    """创建 MCP API Key；明文 key 仅在此次响应中返回。"""
    count_result = await db.execute(
        select(func.count(McpApiKey.id)).where(
            McpApiKey.user_id == user_id,
            McpApiKey.revoked_at.is_(None),
        )
    )
    active_count = count_result.scalar() or 0
    if active_count >= MAX_KEYS_PER_USER:
        raise ValueError(f"每用户最多 {MAX_KEYS_PER_USER} 个未吊销 Key")

    raw_key = _generate_raw_key()
    record = McpApiKey(
        id=generate(size=20),
        user_id=user_id,
        name=name or "",
        key_prefix=raw_key[:24],
        key_hash=_hash_key(raw_key),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "id": record.id,
        "key": raw_key,
        "keyPrefix": record.key_prefix,
        "name": record.name,
        "claudeConfig": build_claude_config(raw_key, public_url),
        "createdAt": record.created_at.isoformat() if record.created_at else None,
    }


async def list_keys(db: AsyncSession, user_id: str) -> list[dict]:
    """列出用户未吊销的 Key。"""
    result = await db.execute(
        select(McpApiKey)
        .where(
            McpApiKey.user_id == user_id,
            McpApiKey.revoked_at.is_(None),
        )
        .order_by(McpApiKey.created_at.desc())
    )
    return [_key_to_item(record) for record in result.scalars().all()]


async def revoke_key(db: AsyncSession, user_id: str, key_id: str) -> bool:
    """吊销 Key（软删除）；成功返回 True。"""
    result = await db.execute(
        select(McpApiKey).where(
            McpApiKey.id == key_id,
            McpApiKey.user_id == user_id,
            McpApiKey.revoked_at.is_(None),
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return False

    record.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return True


async def resolve_user_by_key(db: AsyncSession, raw_key: str) -> str | None:
    """根据 Header 中的明文 Key 解析 user_id；无效或已吊销返回 None。"""
    if not raw_key.startswith(KEY_PREFIX):
        return None

    key_hash = _hash_key(raw_key)
    result = await db.execute(
        select(McpApiKey.user_id).where(
            McpApiKey.key_hash == key_hash,
            McpApiKey.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def touch_last_used(db: AsyncSession, key_hash: str) -> None:
    """更新 Key 最近使用时间（MCP 校验成功后异步调用）。"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.execute(
        update(McpApiKey)
        .where(McpApiKey.key_hash == key_hash)
        .values(last_used_at=now)
    )
    await db.commit()

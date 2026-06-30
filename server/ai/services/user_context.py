"""用户学习进度快照，供聊天 prompt 注入与 progress 工具复用。"""
import json

from app.database import async_session
from app.services.progress_snapshot import (
    fetch_user_progress_data,
    format_progress_snapshot,
    progress_data_to_json,
)


async def fetch_user_progress_snapshot(user_id: str) -> str:
    async with async_session() as session:
        data = await fetch_user_progress_data(session, user_id)
    if not data:
        return ""
    return format_progress_snapshot(data)


async def fetch_user_progress_json(user_id: str) -> str:
    """供 progress_query 工具返回。"""
    async with async_session() as session:
        data = await fetch_user_progress_data(session, user_id)
    if not data:
        return json.dumps({"error": "用户不存在"}, ensure_ascii=False)
    return progress_data_to_json(data)

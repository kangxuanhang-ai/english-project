from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.mcp_keys import CreateMcpKeyDto
from app.services.mcp_api_key import create_key, list_keys, revoke_key

router = APIRouter(prefix="/api/v1/user/mcp-keys", tags=["mcp-keys"])


@router.get("")
async def get_mcp_keys(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出当前用户未吊销的 MCP API Key。"""
    result = await list_keys(db, user["userId"])
    return {"data": result, "code": 200, "message": "查询成功"}


@router.post("")
async def post_create_mcp_key(
    data: CreateMcpKeyDto,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建 MCP API Key；明文 key 仅在此次响应中返回。"""
    try:
        result = await create_key(
            db, user["userId"], data.name, settings.mcp_public_url
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"data": result, "code": 200, "message": "创建成功"}


@router.delete("/{key_id}")
async def delete_mcp_key(
    key_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """吊销 MCP API Key。"""
    ok = await revoke_key(db, user["userId"], key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key 不存在或已吊销")
    return {"data": {"revoked": True, "id": key_id}, "code": 200, "message": "吊销成功"}

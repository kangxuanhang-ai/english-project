from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.external_mcp import UpsertExternalMcpDto
from app.services import user_mcp_connection as user_mcp_service

router = APIRouter(prefix="/api/v1/user/external-mcp", tags=["external-mcp"])


@router.get("")
async def list_external_mcp(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await user_mcp_service.list_available_for_user(db, user["userId"])
    return {"data": data, "code": 200, "message": "查询成功"}


@router.put("/{template_alias}")
async def upsert_external_mcp(
    template_alias: str,
    body: UpsertExternalMcpDto,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await user_mcp_service.upsert_connection(
            db,
            user["userId"],
            template_alias,
            body.enabled,
            body.headers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"data": data, "code": 200, "message": "保存成功"}


@router.post("/{template_alias}/test")
async def test_external_mcp(
    template_alias: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await user_mcp_service.test_user_connection(db, user["userId"], template_alias)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"连接失败: {exc}") from exc
    return {"data": data, "code": 200, "message": "测试成功"}


@router.delete("/{template_alias}")
async def delete_external_mcp(
    template_alias: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await user_mcp_service.delete_connection(db, user["userId"], template_alias)
    if not ok:
        raise HTTPException(status_code=404, detail="连接不存在")
    return {"data": {"deleted": True}, "code": 200, "message": "已禁用"}

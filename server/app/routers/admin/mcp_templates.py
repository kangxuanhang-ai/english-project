from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.schemas.mcp_templates import UpdateMcpTemplateDto
from app.services import mcp_template as mcp_template_service

router = APIRouter(prefix="/mcp-templates", tags=["admin-mcp-templates"])


@router.get("")
async def admin_list_mcp_templates(
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await mcp_template_service.list_templates(db)
    return {"data": data, "code": 200, "message": "查询成功"}


@router.get("/{template_id}")
async def admin_get_mcp_template(
    template_id: str,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    template = await mcp_template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {
        "data": mcp_template_service.template_to_dict(template),
        "code": 200,
        "message": "查询成功",
    }


@router.put("/{template_id}")
async def admin_update_mcp_template(
    template_id: str,
    body: UpdateMcpTemplateDto,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await mcp_template_service.update_template(db, template_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"data": data, "code": 200, "message": "更新成功"}


@router.post("/{template_id}/test")
async def admin_test_mcp_template(
    template_id: str,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await mcp_template_service.test_template_connection(db, template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"连接失败: {exc}") from exc
    return {"data": data, "code": 200, "message": "测试成功"}

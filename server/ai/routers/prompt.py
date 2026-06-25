from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from ai.services.prompt import get_prompt_list

router = APIRouter(prefix="/ai/v1/prompt", tags=["prompt"])


@router.get("/list")
async def list_prompts(user: dict = Depends(get_current_user)):
    """Prompt 列表（需登录）。"""
    result = get_prompt_list()
    return {"data": result, "code": 200, "message": "查询成功"}

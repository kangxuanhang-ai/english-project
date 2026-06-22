# server/ai/routers/recommend.py
from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from ai.services.recommendation import get_recommendation

router = APIRouter(prefix="/ai/v1/recommend", tags=["recommend"])


@router.get("")
async def recommend(
    force: bool = Query(default=False, description="强制刷新推荐"),
    user: dict = Depends(get_current_user),
):
    """获取 AI 课程推荐与学习计划。"""
    user_id = user["userId"]

    result = await get_recommendation(user_id, force=force)
    return result

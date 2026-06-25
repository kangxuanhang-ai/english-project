# server/ai/routers/recommend.py
from fastapi import APIRouter, Depends, Query, Request

from app.dependencies import get_current_user
from ai.rate_limit import limiter
from ai.services.recommendation import get_recommendation, clear_cache_async

router = APIRouter(prefix="/ai/v1/recommend", tags=["recommend"])


@router.get("")
@limiter.limit("10/minute")
async def recommend(
    request: Request,
    force: bool = Query(default=False, description="强制刷新推荐"),
    user: dict = Depends(get_current_user),
):
    """获取 AI 课程推荐与学习计划。"""
    user_id = user["userId"]
    result = await get_recommendation(user_id, force=force)
    return result


@router.post("/cache/clear")
async def clear_recommend_cache(user: dict = Depends(get_current_user)):
    """学习/打卡/购课后清除推荐缓存，下次推荐将基于最新数据生成。"""
    await clear_cache_async(user["userId"])
    return {"data": None, "code": 200, "message": "推荐缓存已清除"}

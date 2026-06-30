"""课程推荐只读封装（供 MCP 复用，不含购课）。"""
from ai.services.recommendation import get_last_recommended_titles, get_recommendation


async def recommend_for_user(
    user_id: str,
    *,
    count: int = 1,
    prefer_different: bool = False,
) -> dict:
    count = min(3, max(1, count))
    exclude = get_last_recommended_titles(user_id) if prefer_different else []
    return await get_recommendation(
        user_id,
        force=prefer_different or bool(exclude),
        count=count,
        exclude_titles=exclude,
    )

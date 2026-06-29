# server/ai/services/tools/recommend.py
import json

from langchain_core.tools import tool
from ai.services.recommendation import (
    get_recommendation,
    format_recommendation_for_agent,
    get_last_recommended_titles,
)
from ai.services.conversation_recommend_cache import set_cached_conversation_recommend


def make_course_recommendation(user_id: str, conversation_id: str):
    """返回绑定了 user_id 与 conversation_id 的 course_recommendation 工具"""

    @tool
    async def course_recommendation(
        count: int = 1, prefer_different: bool = False
    ) -> str:
        """根据用户学习数据推荐课程和制定学习计划。
        当用户询问推荐课程、学习计划、下一步学什么、帮我规划学习时使用。

        Args:
            count: 推荐课程数量。用户说「一门/1个」填 1，「两门」填 2，「三门」填 3，未说明时默认 1。
            prefer_different: 用户说「再推荐一门/换一门/别的课程」时为 True，避免重复上一轮首推。
        """
        exclude = get_last_recommended_titles(user_id) if prefer_different else []
        result = await get_recommendation(
            user_id,
            force=prefer_different or bool(exclude),
            count=count,
            exclude_titles=exclude,
        )
        await set_cached_conversation_recommend(conversation_id, result)
        readable = format_recommendation_for_agent(result)
        payload = json.dumps(result, ensure_ascii=False)
        return f"{readable}\n\n__RECOMMEND_JSON__\n{payload}\n__END_RECOMMEND_JSON__"

    return course_recommendation

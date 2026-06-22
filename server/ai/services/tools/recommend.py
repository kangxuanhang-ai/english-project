# server/ai/services/tools/recommend.py
import json
from langchain_core.tools import tool
from ai.services.recommendation import get_recommendation


def make_course_recommendation(user_id: str):
    """返回绑定了 user_id 的 course_recommendation 工具"""

    @tool
    async def course_recommendation() -> str:
        """根据用户学习数据推荐课程和制定学习计划。
        当用户询问推荐课程、学习计划、下一步学什么、帮我规划学习时使用。"""
        result = await get_recommendation(user_id)
        return json.dumps(result, ensure_ascii=False)

    return course_recommendation

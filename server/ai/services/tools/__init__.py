# server/ai/services/tools/__init__.py
from .word import word_lookup
from .search import web_search
from .grammar import grammar_check
from .progress import make_progress_query
from .recommend import make_course_recommendation

# 保留 base_tools 用于非用户相关场景（如测试）
base_tools = [word_lookup, web_search, grammar_check]


def make_tools(user_id: str) -> list:
    """创建绑定用户 ID 的工具列表"""
    progress_query = make_progress_query(user_id)
    course_recommendation = make_course_recommendation(user_id)
    return [word_lookup, web_search, grammar_check, progress_query, course_recommendation]

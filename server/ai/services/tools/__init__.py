# server/ai/services/tools/__init__.py
from .word import word_lookup
from .search import web_search
from .grammar import make_grammar_check
from .progress import make_progress_query
from .recommend import make_course_recommendation
from .purchase import make_course_purchase
from .knowledge import knowledge_search

base_tools = [word_lookup, web_search]


def make_tools(
    user_id: str, conversation_id: str, *, include_web_search: bool = False
) -> list:
    """创建绑定用户 ID 与对话 ID 的工具列表（normal 角色）"""
    progress_query = make_progress_query(user_id)
    course_recommendation = make_course_recommendation(user_id, conversation_id)
    course_purchase = make_course_purchase(user_id, conversation_id)
    grammar_check = make_grammar_check(user_id)
    tools = [
        word_lookup,
        knowledge_search,
        grammar_check,
        progress_query,
        course_recommendation,
        course_purchase,
    ]
    if include_web_search:
        tools.insert(2, web_search)
    return tools


def make_tools_by_role(
    user_id: str,
    role: str,
    conversation_id: str,
    *,
    web_search_enabled: bool = False,
    web_search_preloaded: bool = False,
) -> list:
    """按角色返回工具列表。仅用户开启联网搜索时挂载 web_search（预搜时不再重复挂载）。"""
    if role == "normal":
        return make_tools(
            user_id,
            conversation_id,
            include_web_search=web_search_enabled and not web_search_preloaded,
        )
    if role == "oral":
        return [make_grammar_check(user_id)]
    return []

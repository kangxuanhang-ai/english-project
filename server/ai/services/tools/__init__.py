# server/ai/services/tools/__init__.py
from .word import word_lookup
from .search import web_search
from .grammar import make_grammar_check
from .progress import make_progress_query
from .my_words import make_add_my_words
from .recommend import make_course_recommendation
from .purchase import make_course_purchase
from .knowledge import knowledge_search

base_tools = [word_lookup, web_search]


def make_tools(
    user_id: str,
    conversation_id: str,
    *,
    include_web_search: bool = False,
    web_mode: bool = False,
    external_tools: list | None = None,
    fetch_url_mode: bool = False,
    fetch_preloaded: bool = False,
) -> list:
    """创建绑定用户 ID 与对话 ID 的工具列表（normal 角色）。

    web_mode=True（自动/手动联网）：不挂载 knowledge_search，避免天气等实时问题误走知识库。
    fetch_url_mode=True：用户消息含 URL 且已挂载 fetch 工具时，跳过 knowledge_search 并优先 fetch。
    fetch_preloaded=True：URL 已预抓取注入 prompt，不再挂载 fetch 工具。
    """
    progress_query = make_progress_query(user_id)
    add_my_words = make_add_my_words(user_id)
    course_recommendation = make_course_recommendation(user_id, conversation_id)
    course_purchase = make_course_purchase(user_id, conversation_id)
    grammar_check = make_grammar_check(user_id)
    tools = [word_lookup]
    if not web_mode and not fetch_url_mode:
        tools.append(knowledge_search)
    tools.extend([grammar_check, progress_query, add_my_words, course_recommendation, course_purchase])
    if include_web_search:
        tools.insert(1 if web_mode else 2, web_search)
    if external_tools:
        fetch_tools = [t for t in external_tools if t.name.startswith("fetch__")]
        other_external = [t for t in external_tools if t not in fetch_tools]
        mount_fetch = fetch_tools and fetch_url_mode and not fetch_preloaded
        if mount_fetch:
            for idx, tool in enumerate(fetch_tools):
                tools.insert(1 + idx, tool)
        if other_external:
            tools.extend(other_external)
        elif not mount_fetch and not fetch_preloaded:
            tools.extend(external_tools)
    return tools


def make_tools_by_role(
    user_id: str,
    role: str,
    conversation_id: str,
    *,
    web_search_enabled: bool = False,
    web_search_preloaded: bool = False,
    external_tools: list | None = None,
    fetch_url_mode: bool = False,
    fetch_preloaded: bool = False,
) -> list:
    """按角色返回工具列表。web_search_preloaded=True 表示 Bocha 预搜已成功，不再挂载 web_search 工具。"""
    if role == "normal":
        return make_tools(
            user_id,
            conversation_id,
            include_web_search=web_search_enabled and not web_search_preloaded,
            web_mode=web_search_enabled,
            external_tools=external_tools,
            fetch_url_mode=fetch_url_mode,
            fetch_preloaded=fetch_preloaded,
        )
    if role == "oral":
        return [make_grammar_check(user_id)]
    return []

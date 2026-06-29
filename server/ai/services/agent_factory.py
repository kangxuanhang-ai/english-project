from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from ai.services.middleware.chat_prompt import ChatContext, chat_dynamic_prompt

_agent_cache: dict[tuple, object] = {}


def agent_cache_key(role: str, deep_think: bool, web_search: bool) -> tuple | None:
    """web_search 时 prompt 动态变化；normal 有 per-user 闭包 tools — 均不缓存。"""
    if web_search:
        return None
    if role == "normal":
        return None
    return (role, deep_think)


def get_or_create_agent(
    *,
    model: BaseChatModel,
    tools: list,
    checkpointer,
    cache_key: tuple | None,
) -> object:
    if cache_key and cache_key in _agent_cache:
        return _agent_cache[cache_key]

    agent = create_agent(
        model=model,
        tools=tools,
        checkpointer=checkpointer,
        middleware=[chat_dynamic_prompt],
        context_schema=ChatContext,
    )
    if cache_key:
        _agent_cache[cache_key] = agent
    return agent


def clear_agent_cache() -> None:
    _agent_cache.clear()

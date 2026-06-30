"""从 LangSmith Hub 拉取角色 system prompt，失败时回退本地 prompt.py。"""
from __future__ import annotations

import asyncio
import logging
import time

from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client

from ai.config import ai_settings
from ai.services.prompt import get_local_role_prompt

logger = logging.getLogger(__name__)

# Hub 标识符前缀。设计文档写 english/chat-{role}，但 LangSmith 将 / 解析为租户分隔符，
# 故实际使用 english-chat-{role}（如 english-chat-normal）。
HUB_PROMPT_PREFIX = "english-chat"
_CACHE_TTL_SEC = 300

_cache: dict[str, tuple[str, float]] = {}
_cache_lock = asyncio.Lock()


def hub_prompt_id(role: str) -> str:
    return f"{HUB_PROMPT_PREFIX}-{role}"


def _hub_enabled() -> bool:
    return bool(ai_settings.langchain_api_key.strip())


def _extract_system_text(prompt: ChatPromptTemplate) -> str:
    if not prompt.messages:
        raise ValueError("Hub prompt has no messages")
    first = prompt.messages[0]
    inner = getattr(first, "prompt", None)
    if inner is not None and hasattr(inner, "template"):
        return str(inner.template)
    content = getattr(first, "content", None)
    if content is not None:
        return str(content)
    raise ValueError(f"cannot extract system text from {type(first)!r}")


def _pull_sync(identifier: str) -> str:
    client = Client(api_key=ai_settings.langchain_api_key)
    tmpl = client.pull_prompt(identifier)
    if not isinstance(tmpl, ChatPromptTemplate):
        raise TypeError(f"expected ChatPromptTemplate, got {type(tmpl)!r}")
    return _extract_system_text(tmpl)


async def get_role_base_prompt(role: str) -> str:
    """拉取角色 base system prompt；Hub 不可用或未配置 key 时用本地副本。"""
    if not _hub_enabled():
        return _append_local_supplement(role, get_local_role_prompt(role))

    now = time.monotonic()
    async with _cache_lock:
        cached = _cache.get(role)
        if cached is not None and (now - cached[1]) < _CACHE_TTL_SEC:
            return _append_local_supplement(role, cached[0])

    identifier = hub_prompt_id(role)
    try:
        text = await asyncio.to_thread(_pull_sync, identifier)
    except Exception as exc:
        logger.warning("LangSmith prompt fallback for role=%s: %s", role, exc)
        return _append_local_supplement(role, get_local_role_prompt(role))

    async with _cache_lock:
        _cache[role] = (text, time.monotonic())
    return _append_local_supplement(role, text)


def _append_local_supplement(role: str, text: str) -> str:
    """Hub prompt 可能滞后于代码；追加本地工具能力说明。"""
    if role != "normal":
        return text
    supplement = """

【平台能力补充 — 本地注入】
- add_my_words：将英文单词加入用户生词本（复习中）。
- 用户说「加入生词本」「收藏这些词」「把这些单词放进生词本」时，**必须调用 add_my_words** 或依据已注入的执行结果回复。
- 写入成功后明确说「已加入生词本复习中」，**禁止**用「学习计划」「去课程学习」代替。
- **禁止**声称无权限、无法操作或只能手动收藏。
"""
    if "add_my_words" in text:
        return text
    return text + supplement

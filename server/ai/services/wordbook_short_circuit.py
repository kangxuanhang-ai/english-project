"""生词本写入：在路由层优先拦截，直接写库并返回 SSE，不经过 LLM。"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

WORDBOOK_FEATURE = "wordbook-short-circuit-v3"

_WORDBOOK_INTENT_RE = re.compile(
    r"生词本|生词库|单词库|词库|复习中|"
    r"放(?:入|到|在).*(?:生词|单词|词库)|"
    r"收藏.*词|加入.*词|放进.*词|加到.*词|添加.*词|"
    r"都放|都给我放|全部放|当前学习"
)
_ENGLISH_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z'-]{0,28}")
_VOCAB_BEFORE_CN_RE = re.compile(r"\b([A-Za-z][a-zA-Z'-]{1,28})\s*[（(]")
_VOCAB_BACKTICK_RE = re.compile(r"`([a-zA-Z][a-zA-Z'-]{0,29})`")
_VOCAB_LIST_RE = re.compile(r"^[\d\-*•]+\s*\*?\*?([a-zA-Z][a-zA-Z'-]{0,29})", re.M)
_VOCAB_TABLE_RE = re.compile(
    r"^\|\s*(?:\d+\s*\|)?\s*([a-zA-Z][a-zA-Z'-]{1,29})\s*\|", re.M
)
_EN_WORD_INLINE_RE = re.compile(r"\b[a-zA-Z][a-zA-Z'-]{1,29}\b")
_WORDBOOK_SKIP = frozenset({
    "the", "a", "an", "and", "or", "to", "of", "in", "for", "is", "are", "was", "were",
    "with", "on", "at", "by", "from", "as", "it", "this", "that", "you", "your", "we",
    "they", "he", "she", "read", "aloud", "http", "https", "www", "com",
    "host", "top", "calls", "supports", "avoid", "making", "values", "wikipedia",
})
_WORDBOOK_PRELOAD_ID = "preload-add-my-words"
_LEMMA_MAP = {"archived": "archive", "reflecting": "reflect", "notate": "notation"}


def is_wordbook_intent(content: str) -> bool:
    return bool(_WORDBOOK_INTENT_RE.search(content))


def _chat_sse(content: str) -> str:
    return f"data: {json.dumps({'type': 'chat', 'role': 'ai', 'content': content}, ensure_ascii=False)}\n\n"


def _done_sse() -> str:
    return f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"


def _extract_inline_english(text: str, *, min_len: int = 2) -> list[str]:
    words: list[str] = []
    for token in _ENGLISH_TOKEN_RE.findall(text):
        lw = token.lower()
        if len(lw) >= min_len and lw not in _WORDBOOK_SKIP:
            words.append(lw)
    return words


def _extract_vocab_words(text: str) -> list[str]:
    candidates: list[str] = []
    for bold in re.findall(r"\*\*([^*]+)\*\*", text):
        candidates.extend(_EN_WORD_INLINE_RE.findall(bold))
    for ticked in _VOCAB_BACKTICK_RE.findall(text):
        candidates.append(ticked)
    candidates.extend(_VOCAB_LIST_RE.findall(text))
    candidates.extend(_VOCAB_TABLE_RE.findall(text))
    candidates.extend(_VOCAB_BEFORE_CN_RE.findall(text))
    candidates.extend(
        re.findall(r"^\s*\d+\.?\s+([a-zA-Z][a-zA-Z'-]{2,29})\b", text, re.M)
    )
    if not candidates:
        candidates.extend(_extract_inline_english(text))
    if not candidates:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for word in candidates:
        lw = _LEMMA_MAP.get(word.lower().strip(), word.lower().strip())
        if lw and lw not in seen:
            seen.add(lw)
            result.append(lw)
    return result[:80]


def _dedupe_words(words: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for word in words:
        lw = word.lower().strip()
        if lw and lw not in seen:
            seen.add(lw)
            result.append(lw)
    return result[:80]


def _words_from_word_lookup_output(content: str) -> list[str]:
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return []
    words: list[str] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("word"):
                words.append(str(item["word"]).lower())
    elif isinstance(data, dict) and data.get("word"):
        words.append(str(data["word"]).lower())
    return words


def _source_messages_for_wordbook(messages: list) -> list:
    cutoff = len(messages)
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if getattr(msg, "type", "") != "human":
            continue
        if _WORDBOOK_INTENT_RE.search(str(getattr(msg, "content", "") or "")):
            cutoff = i
            break
    return messages[:cutoff]


async def _collect_words_from_thread(conversation_id: str) -> list[str]:
    from ai.services.chat import get_checkpointer

    if not conversation_id:
        return []
    try:
        checkpointer = await get_checkpointer()
        state = await checkpointer.aget({"configurable": {"thread_id": conversation_id}})
    except Exception as exc:
        logger.warning("wordbook preload: checkpointer error: %s", exc)
        return []

    if not state:
        return []
    messages = state.get("channel_values", {}).get("messages") or []
    if not messages:
        return []

    source = _source_messages_for_wordbook(messages)
    collected: list[str] = []
    for msg in source:
        if getattr(msg, "type", "") == "tool" and getattr(msg, "name", "") == "word_lookup":
            collected.extend(_words_from_word_lookup_output(msg.content or ""))
        elif getattr(msg, "type", "") == "ai":
            raw = msg.content or ""
            if raw:
                collected.extend(_extract_vocab_words(str(raw)))
    return _dedupe_words(collected)


async def _words_from_recent_ai_messages(conversation_id: str) -> list[str]:
    from ai.services.chat import get_chat_history

    words = await _collect_words_from_thread(conversation_id)
    if words:
        return words
    try:
        history = await get_chat_history(conversation_id, limit=8)
    except Exception as exc:
        logger.warning("wordbook preload: history unavailable: %s", exc)
        return []
    for msg in reversed(history.get("messages", [])):
        if msg.get("role") != "ai":
            continue
        parts = [msg.get("content") or "", msg.get("contentAfter") or ""]
        if msg.get("toolSummary"):
            parts.append(str(msg["toolSummary"]))
        text = "\n".join(str(p) for p in parts if p)
        words = _extract_vocab_words(text)
        if words:
            return words
    return []


async def _preload_add_my_words(
    user_id: str, conversation_id: str, content: str
) -> tuple[dict | None, list[str]]:
    from app.database import async_session
    from app.services.my_words import add_words

    words = _extract_inline_english(content)
    if not words:
        words = _extract_vocab_words(content)
    if not words:
        words = await _words_from_recent_ai_messages(conversation_id)
    if not words:
        return None, []

    async with async_session() as db:
        result = await add_words(db, user_id, words)
    return result, words


def _wordbook_preload_sse(words: list[str], result: dict) -> list[str]:
    call_id = _WORDBOOK_PRELOAD_ID
    tool_input = json.dumps({"words": words}, ensure_ascii=False)
    output = json.dumps(result, ensure_ascii=False)
    return [
        f"data: {json.dumps({'type': 'tool', 'id': call_id, 'tool': 'add_my_words', 'input': tool_input}, ensure_ascii=False)}\n\n",
        f"data: {json.dumps({'type': 'tool_result', 'id': call_id, 'tool': 'add_my_words', 'output': output}, ensure_ascii=False)}\n\n",
    ]


def _format_wordbook_reply(result: dict, words: list[str]) -> str:
    added = result.get("added") or []
    skipped = result.get("skipped") or []
    if added:
        lines = [
            f"已将 **{len(added)}** 个单词加入生词本（复习中）：",
            ", ".join(f"`{w}`" for w in added),
            "",
            "请到顶部 **生词本 → 复习中** 查看。",
        ]
        if skipped:
            lines.append("")
            lines.append(f"另有 {len(skipped)} 个未加入：")
            for item in skipped[:6]:
                lines.append(f"- {item}")
        return "\n".join(lines)

    lines = ["本次**没有**单词写入生词本。"]
    if words:
        lines.append(f"候选词：{', '.join(words[:12])}")
    if skipped:
        lines.append("")
        for item in skipped[:8]:
            lines.append(f"- {item}")
    return "\n".join(lines)


def _format_wordbook_no_words_reply() -> str:
    return (
        "未能从本次对话中识别出要收藏的英文单词。\n\n"
        "请先让我列出单词，再说「放入单词库」。"
    )


async def _persist_wordbook_turn(conversation_id: str, user_content: str, ai_content: str) -> None:
    from langchain.agents import create_agent

    from ai.services.chat import get_checkpointer
    from ai.services.llm import get_llm
    from ai.services.middleware.chat_prompt import ChatContext, chat_dynamic_prompt

    if not conversation_id:
        return
    try:
        checkpointer = await get_checkpointer()
        agent = create_agent(
            model=get_llm(False),
            tools=[],
            checkpointer=checkpointer,
            middleware=[chat_dynamic_prompt],
            context_schema=ChatContext,
        )
        await agent.aupdate_state(
            {"configurable": {"thread_id": conversation_id}},
            {"messages": [HumanMessage(content=user_content), AIMessage(content=ai_content)]},
        )
    except Exception as exc:
        logger.warning("wordbook persist failed: %s", exc)


async def iter_wordbook_sse(
    *,
    role: str,
    user_id: str,
    conversation_id: str,
    content: str,
) -> AsyncIterator[str]:
    """生词本意图：直接写库并 yield SSE；非意图则立即结束（不 yield）。"""
    if role != "normal" or not user_id or not is_wordbook_intent(content):
        return

    logger.info("%s triggered: user=%s content=%s", WORDBOOK_FEATURE, user_id, content[:80])

    wb_result, wb_words = await _preload_add_my_words(user_id, conversation_id, content)
    if wb_result is not None:
        reply = _format_wordbook_reply(wb_result, wb_words)
        events = _wordbook_preload_sse(wb_words, wb_result)
        logger.info(
            "%s done: added=%s skipped=%s",
            WORDBOOK_FEATURE,
            wb_result.get("added"),
            wb_result.get("skipped"),
        )
    else:
        reply = _format_wordbook_no_words_reply()
        events = []
        logger.info("%s no words extracted", WORDBOOK_FEATURE)

    for event in events:
        yield event
    yield _chat_sse(reply)
    yield _done_sse()
    await _persist_wordbook_turn(conversation_id, content, reply)


async def stream_wordbook_short_circuit(
    *,
    role: str,
    user_id: str,
    conversation_id: str,
    content: str,
) -> AsyncIterator[str] | None:
    """兼容旧调用：有意图则返回 async generator，否则 None。"""
    if role != "normal" or not user_id or not is_wordbook_intent(content):
        return None
    return iter_wordbook_sse(
        role=role,
        user_id=user_id,
        conversation_id=conversation_id,
        content=content,
    )

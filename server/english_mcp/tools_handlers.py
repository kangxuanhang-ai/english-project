import json
from typing import Union

from app.services.course_catalog import list_published_courses
from app.services.course_recommend_readonly import recommend_for_user
from app.services.grammar_check import check_grammar
from app.services.knowledge_search_service import search_knowledge_for_query
from app.services.progress_snapshot import fetch_user_progress_data, progress_data_to_json
from app.services.my_words import add_words, list_my_words, mark_mastered
from app.services.word_lookup import lookup_words as lookup_words_service
from english_mcp import db as mcp_db
from english_mcp.auth import rate_limit_key, resolve_progress_user_id
from english_mcp.config import mcp_settings
from english_mcp.context import get_mcp_user
from english_mcp.rate_limit import allow_grammar
from english_mcp.runtime import is_http_mode


def _require_session():
    if mcp_db.async_session is None:
        raise RuntimeError("数据库未初始化")
    return mcp_db.async_session


def normalize_words(words: Union[list[str], str]) -> list[str]:
    if isinstance(words, str):
        return [words]
    return words


async def run_lookup_words(words: Union[list[str], str]) -> str:
    normalized = normalize_words(words)
    session_factory = _require_session()
    async with session_factory() as session:
        results = await lookup_words_service(session, normalized)
    return json.dumps(results, ensure_ascii=False)


async def run_check_grammar(text: str) -> str:
    if is_http_mode() and mcp_settings.mcp_grammar_require_key and not get_mcp_user():
        return "语法检查需要 ENGLISH-MCP-API-KEY，请在平台设置页生成"
    key = rate_limit_key()
    anonymous = is_http_mode() and not get_mcp_user()
    if not allow_grammar(key, anonymous=anonymous):
        return "语法检查请求过于频繁，请稍后再试。"
    return await check_grammar(text)


async def run_get_learning_progress() -> str:
    user_id, err = resolve_progress_user_id()
    if err or not user_id:
        return json.dumps({"error": err or "未授权"}, ensure_ascii=False)
    session_factory = _require_session()
    async with session_factory() as session:
        data = await fetch_user_progress_data(session, user_id)
    if not data:
        return json.dumps({"error": "用户不存在"}, ensure_ascii=False)
    return progress_data_to_json(data)


async def run_search_knowledge(query: str) -> str:
    session_factory = _require_session()
    async with session_factory() as session:
        result = await search_knowledge_for_query(session, query)
    return json.dumps(result, ensure_ascii=False)


async def run_list_courses() -> str:
    session_factory = _require_session()
    async with session_factory() as session:
        courses = await list_published_courses(session)
    return json.dumps({"courses": courses, "total": len(courses)}, ensure_ascii=False)


async def run_recommend_courses(count: int = 1, prefer_different: bool = False) -> str:
    user_id, err = resolve_progress_user_id()
    if err or not user_id:
        return json.dumps({"error": err or "未授权"}, ensure_ascii=False)
    result = await recommend_for_user(
        user_id, count=count, prefer_different=prefer_different
    )
    return json.dumps(result, ensure_ascii=False)


async def run_courses_catalog_resource() -> str:
    return await run_list_courses()


async def run_user_progress_resource() -> str:
    return await run_get_learning_progress()


def _resolve_auth_user() -> tuple[str | None, str | None]:
    return resolve_progress_user_id()


async def run_list_my_words(
    status: str = "learning", page: int = 1, page_size: int = 12
) -> str:
    user_id, err = _resolve_auth_user()
    if err or not user_id:
        return json.dumps({"error": err or "未授权"}, ensure_ascii=False)
    if status not in ("learning", "mastered"):
        return json.dumps({"error": "status 须为 learning 或 mastered"}, ensure_ascii=False)
    session_factory = _require_session()
    async with session_factory() as session:
        result = await list_my_words(session, user_id, status, page, page_size)
    return json.dumps(result, ensure_ascii=False)


async def run_add_words_to_review(words: Union[list[str], str]) -> str:
    user_id, err = _resolve_auth_user()
    if err or not user_id:
        return json.dumps({"error": err or "未授权"}, ensure_ascii=False)
    normalized = normalize_words(words)
    session_factory = _require_session()
    async with session_factory() as session:
        result = await add_words(session, user_id, normalized)
    return json.dumps(result, ensure_ascii=False)


async def run_mark_words_mastered(
    word_ids: list[str] | None = None,
    words: Union[list[str], str, None] = None,
) -> str:
    user_id, err = _resolve_auth_user()
    if err or not user_id:
        return json.dumps({"error": err or "未授权"}, ensure_ascii=False)
    word_id_list = list(word_ids) if word_ids else None
    word_list: list[str] | None = None
    if words is not None:
        word_list = normalize_words(words) if isinstance(words, str) else list(words)
    if not word_id_list and not word_list:
        return json.dumps({"error": "请提供 word_ids 或 words"}, ensure_ascii=False)
    session_factory = _require_session()
    async with session_factory() as session:
        result = await mark_mastered(
            session, user_id, word_ids=word_id_list, words=word_list
        )
    return json.dumps(result, ensure_ascii=False)


async def run_platform_health() -> str:
    from sqlalchemy import func, select, text

    from app.models.word_book import WordBook

    payload: dict = {
        "database": "down",
        "wordBookCount": 0,
        "deepseekConfigured": bool(mcp_settings.deepseek_api_key.strip()),
    }
    try:
        session_factory = _require_session()
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
            count = (await session.execute(select(func.count(WordBook.id)))).scalar() or 0
            payload["database"] = "up"
            payload["wordBookCount"] = count
    except Exception as exc:
        payload["error"] = str(exc)
    return json.dumps(payload, ensure_ascii=False)

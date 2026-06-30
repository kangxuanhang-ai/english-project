import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Union

from mcp.server.fastmcp import FastMCP

from english_mcp.config import mcp_settings
from english_mcp import db as mcp_db
from english_mcp.tools_handlers import (
    run_add_words_to_review,
    run_check_grammar,
    run_courses_catalog_resource,
    run_get_learning_progress,
    run_list_courses,
    run_list_my_words,
    run_lookup_words,
    run_mark_words_mastered,
    run_platform_health,
    run_recommend_courses,
    run_search_knowledge,
    run_user_progress_resource,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
    mcp_db.init_db(
        mcp_settings.database_url,
        pool_size=mcp_settings.mcp_db_pool_size,
        max_overflow=mcp_settings.mcp_db_max_overflow,
    )
    logger.info("english_mcp DB pool initialized")
    try:
        yield
    finally:
        await mcp_db.dispose_db()
        logger.info("english_mcp DB pool disposed")


mcp = FastMCP(
    "english",
    lifespan=lifespan,
    host=mcp_settings.mcp_http_host,
    port=mcp_settings.mcp_http_port,
)


@mcp.tool()
async def lookup_words(words: Union[list[str], str]) -> str:
    """批量查询英语单词的详细信息，包括音标、中文释义、词性。传入单词列表，如 ["abandon"]。"""
    return await run_lookup_words(words)


@mcp.tool()
async def check_grammar(text: str) -> str:
    """检查英语句子的语法错误，给出修正建议和错误原因解释。"""
    return await run_check_grammar(text)


@mcp.tool()
async def get_learning_progress() -> str:
    """查询当前用户的学习进度：已掌握单词数、课程完成情况、打卡天数等。需配置 MCP 用户或 demo 用户。"""
    return await run_get_learning_progress()


@mcp.tool()
async def search_knowledge(query: str) -> str:
    """检索平台内部知识库（管理员上传的文档）。适用于课程说明、平台规则、学习方法等。"""
    return await run_search_knowledge(query)


@mcp.tool()
async def list_courses() -> str:
    """列出所有在售课程：名称、价格、简介、讲师。"""
    return await run_list_courses()


@mcp.tool()
async def recommend_courses(count: int = 1, prefer_different: bool = False) -> str:
    """根据用户学习数据推荐课程（1～3 门）与学习计划。需配置 MCP 用户或 demo 用户。"""
    return await run_recommend_courses(count=count, prefer_different=prefer_different)


@mcp.resource("english://courses/catalog")
async def courses_catalog_resource() -> str:
    """已发布课程目录 JSON。"""
    return await run_courses_catalog_resource()


@mcp.resource("english://user/progress")
async def user_progress_resource() -> str:
    """当前 MCP 用户学习进度 JSON。"""
    return await run_user_progress_resource()


@mcp.tool()
async def list_my_words(
    status: str = "learning", page: int = 1, page_size: int = 12
) -> str:
    """列出我的生词本。status: learning（复习中）或 mastered（已掌握）。"""
    return await run_list_my_words(status=status, page=page, page_size=page_size)


@mcp.tool()
async def add_words_to_review(words: Union[list[str], str]) -> str:
    """将单词加入生词本（复习中）。传入单词列表或单个单词字符串。"""
    return await run_add_words_to_review(words)


@mcp.tool()
async def mark_words_mastered(
    word_ids: list[str] | None = None,
    words: Union[list[str], str, None] = None,
) -> str:
    """标记单词为已掌握。可传 word_ids 或 words（单词字符串列表）。"""
    return await run_mark_words_mastered(word_ids=word_ids, words=words)


@mcp.tool()
async def platform_health() -> str:
    """检查平台健康状态：数据库连通、词库条数、DeepSeek 是否配置。"""
    return await run_platform_health()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=__import__("sys").stderr,
    )
    mcp.run()


if __name__ == "__main__":
    main()

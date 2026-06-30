"""MCP tool handlers 冒烟（不经过 stdio）。"""
import asyncio
import json

from english_mcp import db as mcp_db
from english_mcp.config import mcp_settings
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


async def main() -> None:
    mcp_db.init_db(
        mcp_settings.database_url,
        pool_size=mcp_settings.mcp_db_pool_size,
        max_overflow=mcp_settings.mcp_db_max_overflow,
    )
    try:
        out1 = await run_lookup_words(["abandon"])
        print("lookup list:", "abandon" in out1)

        out2 = await run_lookup_words("abandon")
        print("lookup str:", "abandon" in out2)

        courses = json.loads(await run_list_courses())
        print("list_courses:", courses.get("total", 0), "courses")

        catalog = json.loads(await run_courses_catalog_resource())
        print("resource catalog:", catalog.get("total", 0), "courses")

        progress = json.loads(await run_get_learning_progress())
        if "error" in progress:
            print("progress:", progress["error"])
        else:
            print("progress word_count:", progress.get("word_count"))

        resource_progress = json.loads(await run_user_progress_resource())
        print("resource progress keys:", list(resource_progress.keys())[:5])

        kb = json.loads(await run_search_knowledge("学习方法"))
        print("search_knowledge results:", len(kb.get("results", [])))

        if not progress.get("error"):
            rec = json.loads(await run_recommend_courses(count=1))
            print("recommend courses:", len(rec.get("courses", [])))
        else:
            print("recommend: SKIP (no user)")

        if mcp_settings.deepseek_api_key:
            out4 = await run_check_grammar("He go to school yesterday.")
            print("grammar:", out4[:80])
        else:
            print("grammar: SKIP (no DEEPSEEK_API_KEY)")

        health = json.loads(await run_platform_health())
        print(
            "platform_health:",
            health.get("database"),
            "words:",
            health.get("wordBookCount"),
        )

        progress_err = progress.get("error")
        if progress_err:
            print("my_words: SKIP (no user)")
        else:
            added = json.loads(await run_add_words_to_review(["abandon"]))
            print("add_words added:", len(added.get("added", [])))

            learning = json.loads(await run_list_my_words(status="learning"))
            print("list_my_words learning total:", learning.get("total"))

            marked = json.loads(
                await run_mark_words_mastered(words=["abandon"])
            )
            print("mark_mastered newlyMastered:", marked.get("newlyMastered"))

            mastered = json.loads(await run_list_my_words(status="mastered"))
            print("list_my_words mastered total:", mastered.get("total"))

        print("OK")
    finally:
        await mcp_db.dispose_db()


if __name__ == "__main__":
    asyncio.run(main())

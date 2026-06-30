"""用户学习进度快照，供聊天 prompt、progress 工具与 MCP 复用。"""
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, CourseRecord
from app.models.user import User
from app.models.word_book import WordBook, WordBookRecord

MAX_MASTERED_WORDS_IN_PROGRESS = 500


async def fetch_user_progress_data(db: AsyncSession, user_id: str) -> dict | None:
    """查询用户学习进度（实时读库）。"""
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return None

    word_count_result = await db.execute(
        select(func.count(WordBookRecord.id)).where(
            WordBookRecord.user_id == user_id,
            WordBookRecord.is_master.is_(True),
        )
    )
    word_count = word_count_result.scalar() or 0

    since_7d = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    week_result = await db.execute(
        select(func.count(WordBookRecord.id)).where(
            WordBookRecord.user_id == user_id,
            WordBookRecord.is_master.is_(True),
            WordBookRecord.created_at >= since_7d,
        )
    )
    words_this_week = week_result.scalar() or 0

    mastered_words_result = await db.execute(
        select(WordBook.word)
        .join(WordBookRecord, WordBookRecord.word_id == WordBook.id)
        .where(
            WordBookRecord.user_id == user_id,
            WordBookRecord.is_master.is_(True),
        )
        .order_by(WordBookRecord.created_at.desc())
        .limit(MAX_MASTERED_WORDS_IN_PROGRESS)
    )
    mastered_words = [row[0] for row in mastered_words_result.all()]

    course_result = await db.execute(
        select(Course.name, CourseRecord.is_purchased)
        .join(CourseRecord, CourseRecord.course_id == Course.id)
        .where(CourseRecord.user_id == user_id)
    )
    courses = [{"name": row[0], "purchased": row[1]} for row in course_result.all()]
    purchased_names = [c["name"] for c in courses if c["purchased"]]

    return {
        "word_count": word_count,
        "words_this_week": words_this_week,
        "mastered_words": mastered_words,
        "courses": courses,
        "purchased_course_names": purchased_names,
        "day_number": user.day_number or 0,
    }


def format_progress_snapshot(data: dict) -> str:
    """格式化为可注入 system prompt 的简短摘要。"""
    words = data.get("mastered_words", [])
    recent = "、".join(words[:8]) or "暂无"
    purchased = "、".join(data.get("purchased_course_names", [])[:6]) or "暂无"
    word_count = data.get("word_count", 0)
    extra = f"（共 {word_count} 个，此处仅列最近 8 个）" if word_count > 8 else ""
    return f"""【用户当前学习数据（实时，回答时可自然引用，勿提及「快照/系统注入」）】
- 累计打卡：{data.get("day_number", 0)} 天
- 已掌握单词：{word_count} 个（近7天新掌握 {data.get("words_this_week", 0)} 个）
- 已购课程：{len(data.get("purchased_course_names", []))} 门（{purchased}）
- 最近掌握的词{extra}：{recent}"""


def progress_data_to_json(data: dict) -> str:
    """供 progress_query 工具返回的 JSON 字符串。"""
    return json.dumps(
        {
            "word_count": data["word_count"],
            "words_this_week": data["words_this_week"],
            "mastered_words": data["mastered_words"],
            "courses": data["courses"],
            "day_number": data["day_number"],
        },
        ensure_ascii=False,
    )

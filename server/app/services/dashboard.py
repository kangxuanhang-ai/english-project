"""用户学习数据看板聚合"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.word_book import WordBook, WordBookRecord
from app.models.course import Course, CourseRecord
from app.models.visitor import PageView, Visitor

VALID_COURSE_TYPES = {"gk", "zk", "gre", "toefl", "ielts", "cet6", "cet4", "ky"}


async def get_dashboard_stats(db: AsyncSession, user_id: str) -> dict:
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return _empty_dashboard()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since_7d = now - timedelta(days=7)

    mastered_result = await db.execute(
        select(func.count(WordBookRecord.id)).where(
            WordBookRecord.user_id == user_id,
            WordBookRecord.is_master.is_(True),
        )
    )
    mastered_words = mastered_result.scalar() or 0

    week_result = await db.execute(
        select(func.count(WordBookRecord.id)).where(
            WordBookRecord.user_id == user_id,
            WordBookRecord.is_master.is_(True),
            WordBookRecord.created_at >= since_7d,
        )
    )
    words_this_week = week_result.scalar() or 0

    purchased_result = await db.execute(
        select(func.count(CourseRecord.id)).where(
            CourseRecord.user_id == user_id,
            CourseRecord.is_purchased.is_(True),
        )
    )
    purchased_courses = purchased_result.scalar() or 0

    # 近 7 天每日掌握词数
    trend_result = await db.execute(
        select(
            func.date(WordBookRecord.created_at).label("day"),
            func.count(WordBookRecord.id).label("count"),
        )
        .where(
            WordBookRecord.user_id == user_id,
            WordBookRecord.is_master.is_(True),
            WordBookRecord.created_at >= since_7d,
        )
        .group_by(func.date(WordBookRecord.created_at))
        .order_by(func.date(WordBookRecord.created_at))
    )
    word_trend = [
        {"date": str(row.day), "count": row.count}
        for row in trend_result.all()
    ]

    # 已购课程进度
    courses_result = await db.execute(
        select(Course)
        .join(CourseRecord, CourseRecord.course_id == Course.id)
        .where(
            CourseRecord.user_id == user_id,
            CourseRecord.is_purchased.is_(True),
        )
    )
    purchased_list = courses_result.scalars().all()
    course_progress = []
    for course in purchased_list:
        course_type = course.value
        if course_type not in VALID_COURSE_TYPES:
            continue
        col = getattr(WordBook, course_type)
        mastered_col = await db.execute(
            select(func.count(WordBookRecord.id))
            .join(WordBook, WordBook.id == WordBookRecord.word_id)
            .where(
                WordBookRecord.user_id == user_id,
                WordBookRecord.is_master.is_(True),
                col.is_(True),
            )
        )
        total_col = await db.execute(
            select(func.count(WordBook.id)).where(col.is_(True))
        )
        mastered = mastered_col.scalar() or 0
        total = total_col.scalar() or 0
        percent = round(mastered / total * 100, 1) if total > 0 else 0
        course_progress.append({
            "courseId": course.id,
            "name": course.name,
            "mastered": mastered,
            "total": total,
            "percent": percent,
        })

    # Tracker：PV 经 visitor.user_id 关联
    pv_trend_result = await db.execute(
        select(
            func.date(PageView.created_at).label("day"),
            func.count(PageView.id).label("count"),
        )
        .join(Visitor, Visitor.id == PageView.visitor_id)
        .where(
            Visitor.user_id == user_id,
            PageView.created_at >= since_7d,
        )
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
    )
    pv_trend = [
        {"date": str(row.day), "count": row.count}
        for row in pv_trend_result.all()
    ]

    top_paths_result = await db.execute(
        select(PageView.path, func.count(PageView.id).label("count"))
        .join(Visitor, Visitor.id == PageView.visitor_id)
        .where(
            Visitor.user_id == user_id,
            PageView.created_at >= since_7d,
        )
        .group_by(PageView.path)
        .order_by(func.count(PageView.id).desc())
        .limit(5)
    )
    top_paths = [
        {"path": row.path, "count": row.count}
        for row in top_paths_result.all()
    ]

    total_pv_result = await db.execute(
        select(func.count(PageView.id))
        .join(Visitor, Visitor.id == PageView.visitor_id)
        .where(Visitor.user_id == user_id)
    )
    total_pv = total_pv_result.scalar() or 0

    return {
        "overview": {
            "checkInDays": user.day_number or 0,
            "masteredWords": mastered_words,
            "purchasedCourses": purchased_courses,
            "wordsThisWeek": words_this_week,
        },
        "wordTrend": word_trend,
        "courseProgress": course_progress,
        "activity": {
            "pvTrend": pv_trend,
            "topPaths": top_paths,
            "totalPv": total_pv,
        },
    }


def _empty_dashboard() -> dict:
    return {
        "overview": {
            "checkInDays": 0,
            "masteredWords": 0,
            "purchasedCourses": 0,
            "wordsThisWeek": 0,
        },
        "wordTrend": [],
        "courseProgress": [],
        "activity": {"pvTrend": [], "topPaths": [], "totalPv": 0},
    }

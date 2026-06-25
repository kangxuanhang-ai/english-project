"""B 端用户管理"""
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.course import Course, CourseRecord
from app.models.user import User
from app.models.word_book import WordBookRecord


def _user_brief(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "wordNumber": user.word_number,
        "dayNumber": user.day_number,
        "role": user.role,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at else None,
    }


async def list_users(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    role: str | None = None,
) -> dict:
    query = select(User)
    count_query = select(func.count(User.id))

    if role in ("user", "admin"):
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        cond = or_(User.name.ilike(kw), User.phone.ilike(kw), User.email.ilike(kw))
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    list_items = []
    for user in users:
        item = _user_brief(user)
        if user.role == "user":
            mastered = (
                await db.execute(
                    select(func.count(WordBookRecord.id)).where(
                        WordBookRecord.user_id == user.id,
                        WordBookRecord.is_master.is_(True),
                    )
                )
            ).scalar() or 0
            item["masteredWords"] = mastered
        list_items.append(item)

    return {"list": list_items, "total": total}


async def get_user_detail(db: AsyncSession, user_id: str) -> dict | None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None

    mastered_words = (
        await db.execute(
            select(func.count(WordBookRecord.id)).where(
                WordBookRecord.user_id == user_id,
                WordBookRecord.is_master.is_(True),
            )
        )
    ).scalar() or 0

    purchased_count = (
        await db.execute(
            select(func.count(CourseRecord.id)).where(
                CourseRecord.user_id == user_id,
                CourseRecord.is_purchased.is_(True),
            )
        )
    ).scalar() or 0

    courses_result = await db.execute(
        select(CourseRecord)
        .options(joinedload(CourseRecord.course))
        .where(CourseRecord.user_id == user_id, CourseRecord.is_purchased.is_(True))
        .order_by(CourseRecord.created_at.desc())
        .limit(10)
    )
    recent_courses = []
    for record in courses_result.scalars().unique().all():
        c = record.course
        recent_courses.append(
            {
                "id": c.id,
                "name": c.name,
                "value": c.value,
                "purchasedAt": record.created_at.isoformat() if record.created_at else None,
            }
        )

    return {
        **_user_brief(user),
        "masteredWords": mastered_words,
        "purchasedCourses": purchased_count,
        "recentCourses": recent_courses,
    }

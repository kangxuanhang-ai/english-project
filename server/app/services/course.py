from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.course import Course, CourseRecord
from app.models.payment import PaymentRecord, TradeStatus


async def get_course_list(db: AsyncSession, page: int = 1, page_size: int = 12) -> dict:
    """获取所有课程（分页）。对应 NestJS CourseService.findAll"""
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Course)
        .where(Course.is_published.is_(True))
        .offset(offset)
        .limit(page_size)
    )
    courses = result.scalars().all()
    count_result = await db.execute(
        select(func.count(Course.id)).where(Course.is_published.is_(True))
    )
    total = count_result.scalar()
    return {
        "list": [
            {
                "id": c.id,
                "name": c.name,
                "value": c.value,
                "description": c.description,
                "teacher": c.teacher,
                "url": c.url,
                "price": f"{c.price:.2f}",
            }
            for c in courses
        ],
        "total": total,
    }


async def get_my_courses(db: AsyncSession, user_id: str) -> list:
    """获取用户已购课程。对应 NestJS CourseService.findMy"""
    result = await db.execute(
        select(CourseRecord)
        .options(joinedload(CourseRecord.course))
        .join(CourseRecord.payment_record)
        .where(
            CourseRecord.user_id == user_id,
            PaymentRecord.trade_status == TradeStatus.TRADE_SUCCESS,
        )
    )
    records = result.scalars().unique().all()

    courses = []
    for record in records:
        course = record.course
        courses.append({
            "id": course.id,
            "name": course.name,
            "value": course.value,
            "description": course.description,
            "teacher": course.teacher,
            "url": course.url,
            "price": f"{course.price:.2f}",
        })
    return courses


async def get_courses_batch_status(
    db: AsyncSession, user_id: str, course_ids: list[str]
) -> dict:
    """批量查询课程信息与当前用户购买状态"""
    if not course_ids:
        return {"items": [], "missingIds": []}

    result = await db.execute(select(Course).where(Course.id.in_(course_ids)))
    courses = {c.id: c for c in result.scalars().all()}
    found_ids = set(courses.keys())
    missing_ids = [cid for cid in course_ids if cid not in found_ids]

    if not found_ids:
        return {"items": [], "missingIds": missing_ids}

    purchased_result = await db.execute(
        select(CourseRecord.course_id).where(
            CourseRecord.user_id == user_id,
            CourseRecord.is_purchased.is_(True),
            CourseRecord.course_id.in_(found_ids),
        )
    )
    purchased_ids = {row[0] for row in purchased_result.all()}

    items = [
        {
            "id": c.id,
            "name": c.name,
            "value": c.value,
            "description": c.description,
            "teacher": c.teacher,
            "url": c.url,
            "price": f"{c.price:.2f}",
            "purchased": c.id in purchased_ids,
        }
        for c in courses.values()
    ]
    return {"items": items, "missingIds": missing_ids}

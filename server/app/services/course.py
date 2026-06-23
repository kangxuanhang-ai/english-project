from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.course import Course, CourseRecord
from app.models.payment import PaymentRecord, TradeStatus


async def get_course_list(db: AsyncSession, page: int = 1, page_size: int = 12) -> dict:
    """获取所有课程（分页）。对应 NestJS CourseService.findAll"""
    offset = (page - 1) * page_size
    result = await db.execute(select(Course).offset(offset).limit(page_size))
    courses = result.scalars().all()
    # 获取总数
    count_result = await db.execute(select(func.count(Course.id)))
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

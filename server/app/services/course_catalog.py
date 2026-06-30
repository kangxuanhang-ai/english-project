from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course


async def list_published_courses(db: AsyncSession, *, limit: int = 100) -> list[dict]:
    """列出已发布课程（只读，供 MCP / 内部复用）。"""
    result = await db.execute(
        select(Course)
        .where(Course.is_published.is_(True))
        .order_by(Course.name)
        .limit(limit)
    )
    courses = result.scalars().all()
    return [
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
    ]

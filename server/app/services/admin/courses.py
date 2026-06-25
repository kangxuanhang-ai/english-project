"""B 端课程管理"""
import re
import time
from decimal import Decimal
from io import BytesIO

from nanoid import generate
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from shared.minio_client import minio_client, minio_object_public_url

VALID_VALUES = {"gk", "zk", "gre", "toefl", "ielts", "cet6", "cet4", "ky"}
ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_COVER_BYTES = 2 * 1024 * 1024


def _course_item(course: Course) -> dict:
    return {
        "id": course.id,
        "name": course.name,
        "value": course.value,
        "description": course.description,
        "teacher": course.teacher,
        "url": course.url,
        "price": float(course.price),
        "isPublished": course.is_published,
        "createdAt": course.created_at.isoformat() if course.created_at else None,
        "updatedAt": course.updated_at.isoformat() if course.updated_at else None,
    }


async def list_admin_courses(
    db: AsyncSession, *, page: int = 1, page_size: int = 10
) -> dict:
    offset = (page - 1) * page_size
    total = (await db.execute(select(func.count(Course.id)))).scalar() or 0
    result = await db.execute(
        select(Course).order_by(Course.created_at.desc()).offset(offset).limit(page_size)
    )
    courses = result.scalars().all()
    return {"list": [_course_item(c) for c in courses], "total": total}


async def get_course(db: AsyncSession, course_id: str) -> dict | None:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    return _course_item(course) if course else None


async def upload_course_cover(file) -> dict:
    if not file:
        raise ValueError("文件不存在")
    if file.content_type not in ALLOWED_COVER_TYPES:
        raise ValueError("仅支持 JPG/PNG/WebP 格式")
    content = await file.read()
    if len(content) > MAX_COVER_BYTES:
        raise ValueError("封面不能超过 2MB")

    client = minio_client.get_client()
    bucket = minio_client.get_bucket()
    safe_name = re.sub(r"[^\w.\-]", "_", file.filename or "cover.png")
    file_name = f"course-covers/{int(time.time() * 1000)}-{safe_name}"

    client.put_object(
        bucket,
        file_name,
        BytesIO(content),
        length=len(content),
        content_type=file.content_type,
    )

    object_path = f"/{bucket}/{file_name}"
    preview_url = minio_object_public_url(object_path)
    return {"url": preview_url, "path": object_path}


async def create_course(db: AsyncSession, data: dict) -> dict:
    if data["value"] not in VALID_VALUES:
        raise ValueError(f"课程类型无效，允许: {', '.join(sorted(VALID_VALUES))}")
    course = Course(
        id=generate(size=20),
        name=data["name"],
        value=data["value"],
        description=data.get("description"),
        teacher=data["teacher"],
        url=data["url"],
        price=Decimal(str(data["price"])),
        is_published=True,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return _course_item(course)


async def update_course(db: AsyncSession, course_id: str, data: dict) -> dict | None:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        return None
    if "value" in data and data["value"] not in VALID_VALUES:
        raise ValueError(f"课程类型无效，允许: {', '.join(sorted(VALID_VALUES))}")
    for field, attr in [
        ("name", "name"),
        ("value", "value"),
        ("description", "description"),
        ("teacher", "teacher"),
        ("url", "url"),
    ]:
        if field in data and data[field] is not None:
            setattr(course, attr, data[field])
    if "price" in data and data["price"] is not None:
        course.price = Decimal(str(data["price"]))
    await db.commit()
    await db.refresh(course)
    return _course_item(course)


async def set_course_published(db: AsyncSession, course_id: str, published: bool) -> dict | None:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        return None
    course.is_published = published
    await db.commit()
    await db.refresh(course)
    return _course_item(course)

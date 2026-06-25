from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from nanoid import generate

from app.models.visitor import Visitor, PageView, TrackEvent, PerformanceEntry, ErrorEntry


async def upsert_visitor(db: AsyncSession, data: dict) -> str:
    """
    上报/更新访客（UV）。
    对应 NestJS TrackerService.uv。
    """
    result = await db.execute(
        select(Visitor).where(Visitor.anonymous_id == data["anonymousId"])
    )
    visitor = result.scalar_one_or_none()

    if visitor:
        # 更新
        visitor.user_id = data.get("userId")
        visitor.browser = data.get("browser")
        visitor.os = data.get("os")
        visitor.device = data.get("device")
    else:
        # 创建
        visitor = Visitor(
            id=generate(size=20),
            anonymous_id=data["anonymousId"],
            user_id=data.get("userId"),
            browser=data.get("browser"),
            os=data.get("os"),
            device=data.get("device"),
        )
        db.add(visitor)

    await db.flush()
    await db.commit()
    return visitor.id


async def update_visitor(db: AsyncSession, data: dict) -> None:
    """更新访客的 userId。对应 NestJS TrackerService.updateUv"""
    from app.models.user import User

    result = await db.execute(select(Visitor).where(Visitor.id == data["visitorId"]))
    visitor = result.scalar_one_or_none()
    if visitor:
        # 验证 userId 存在（防止外键约束错误）
        user_result = await db.execute(select(User).where(User.id == data["userId"]))
        if user_result.scalar_one_or_none():
            visitor.user_id = data["userId"]
            await db.flush()
            await db.commit()


async def record_pv(db: AsyncSession, data: dict) -> None:
    """记录页面访问。对应 NestJS TrackerService.pv"""
    pv = PageView(
        id=generate(size=20),
        visitor_id=data["visitorId"],
        url=data["url"],
        referrer=data.get("referrer"),
        path=data["path"],
    )
    db.add(pv)
    await db.flush()
    await db.commit()


async def record_event(db: AsyncSession, data: dict) -> None:
    """记录用户行为。对应 NestJS TrackerService.event"""
    event = TrackEvent(
        id=generate(size=20),
        visitor_id=data["visitorId"],
        event=data["event"],
        payload=data.get("payload"),
        url=data.get("url"),
    )
    db.add(event)
    await db.flush()
    await db.commit()


async def record_performance(db: AsyncSession, data: dict) -> None:
    """记录性能指标。对应 NestJS TrackerService.performance"""
    entry = PerformanceEntry(
        id=generate(size=20),
        visitor_id=data["visitorId"],
        fp=data.get("fp"),
        fcp=data.get("fcp"),
        lcp=data.get("lcp"),
        inp=data.get("inp"),
        cls=data.get("cls"),
    )
    db.add(entry)
    await db.flush()
    await db.commit()


async def record_error(db: AsyncSession, data: dict) -> None:
    """记录错误。对应 NestJS TrackerService.error"""
    entry = ErrorEntry(
        id=generate(size=20),
        visitor_id=data["visitorId"],
        error=data["error"],
        message=data.get("message"),
        stack=data.get("stack"),
        url=data.get("url"),
    )
    db.add(entry)
    await db.flush()
    await db.commit()

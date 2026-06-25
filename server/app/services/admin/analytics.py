"""B 端数据监控聚合"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visitor import ErrorEntry, PageView, PerformanceEntry


def _today_start() -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _since_days(days: int) -> datetime:
    today = _today_start()
    return today - timedelta(days=max(days - 1, 0))


async def get_analytics_overview(db: AsyncSession, *, days: int = 7) -> dict:
    since = _since_days(days)

    pv_rows = await db.execute(
        select(
            func.date(PageView.created_at).label("day"),
            func.count(PageView.id).label("count"),
        )
        .where(PageView.created_at >= since)
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
    )
    pv_trend = [{"date": str(r.day), "count": r.count} for r in pv_rows.all()]

    uv_rows = await db.execute(
        select(
            func.date(PageView.created_at).label("day"),
            func.count(func.distinct(PageView.visitor_id)).label("count"),
        )
        .where(PageView.created_at >= since)
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
    )
    uv_trend = [{"date": str(r.day), "count": r.count} for r in uv_rows.all()]

    return {"days": days, "pvTrend": pv_trend, "uvTrend": uv_trend}


async def get_top_pages(db: AsyncSession, *, days: int = 7, limit: int = 20) -> dict:
    since = _since_days(days)
    rows = await db.execute(
        select(PageView.path, func.count(PageView.id).label("count"))
        .where(PageView.created_at >= since)
        .group_by(PageView.path)
        .order_by(func.count(PageView.id).desc())
        .limit(limit)
    )
    return {
        "days": days,
        "list": [{"path": r.path, "count": r.count} for r in rows.all()],
    }


async def list_errors(
    db: AsyncSession, *, page: int = 1, page_size: int = 20
) -> dict:
    total = (await db.execute(select(func.count(ErrorEntry.id)))).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        select(ErrorEntry)
        .order_by(ErrorEntry.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()
    return {
        "list": [
            {
                "id": e.id,
                "error": e.error,
                "message": e.message,
                "stack": e.stack,
                "url": e.url,
                "visitorId": e.visitor_id,
                "createdAt": e.created_at.isoformat() if e.created_at else None,
            }
            for e in items
        ],
        "total": total,
    }


async def get_performance(db: AsyncSession, *, days: int = 7) -> dict:
    since = _since_days(days)

    avg_row = await db.execute(
        select(
            func.avg(PerformanceEntry.fp),
            func.avg(PerformanceEntry.fcp),
            func.avg(PerformanceEntry.lcp),
            func.avg(PerformanceEntry.inp),
            func.avg(PerformanceEntry.cls),
        ).where(PerformanceEntry.created_at >= since)
    )
    fp, fcp, lcp, inp, cls = avg_row.one()

    trend_rows = await db.execute(
        select(
            func.date(PerformanceEntry.created_at).label("day"),
            func.avg(PerformanceEntry.lcp).label("lcp"),
            func.avg(PerformanceEntry.fcp).label("fcp"),
        )
        .where(PerformanceEntry.created_at >= since)
        .group_by(func.date(PerformanceEntry.created_at))
        .order_by(func.date(PerformanceEntry.created_at))
    )
    trend = [
        {
            "date": str(r.day),
            "lcp": round(float(r.lcp), 2) if r.lcp is not None else None,
            "fcp": round(float(r.fcp), 2) if r.fcp is not None else None,
        }
        for r in trend_rows.all()
    ]

    def _round(v):
        return round(float(v), 2) if v is not None else None

    return {
        "days": days,
        "avg": {
            "fp": _round(fp),
            "fcp": _round(fcp),
            "lcp": _round(lcp),
            "inp": _round(inp),
            "cls": _round(cls),
        },
        "trend": trend,
    }

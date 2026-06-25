"""B 端仪表盘聚合"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.payment import PaymentRecord, TradeStatus
from app.models.user import User
from app.models.knowledge import DocumentStatus, KnowledgeDocument
from app.models.visitor import ErrorEntry, PageView


def _today_start() -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def get_admin_dashboard(db: AsyncSession) -> dict:
    today = _today_start()

    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    today_new_users = (
        await db.execute(select(func.count(User.id)).where(User.created_at >= today))
    ).scalar() or 0

    course_count = (await db.execute(select(func.count(Course.id)))).scalar() or 0

    today_orders = (
        await db.execute(
            select(func.count(PaymentRecord.id)).where(
                PaymentRecord.trade_status == TradeStatus.TRADE_SUCCESS,
                PaymentRecord.send_pay_time >= today,
            )
        )
    ).scalar() or 0

    total_revenue_row = await db.execute(
        select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
            PaymentRecord.trade_status == TradeStatus.TRADE_SUCCESS
        )
    )
    total_revenue = float(total_revenue_row.scalar() or 0)

    today_revenue_row = await db.execute(
        select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
            PaymentRecord.trade_status == TradeStatus.TRADE_SUCCESS,
            PaymentRecord.send_pay_time >= today,
        )
    )
    today_revenue = float(today_revenue_row.scalar() or 0)

    knowledge_doc_count = (
        await db.execute(select(func.count(KnowledgeDocument.id)))
    ).scalar() or 0
    knowledge_ready_count = (
        await db.execute(
            select(func.count(KnowledgeDocument.id)).where(
                KnowledgeDocument.status == DocumentStatus.READY.value
            )
        )
    ).scalar() or 0

    unpaid_orders = (
        await db.execute(
            select(func.count(PaymentRecord.id)).where(
                PaymentRecord.trade_status.in_([TradeStatus.NOT_PAY, TradeStatus.WAIT_BUYER_PAY])
            )
        )
    ).scalar() or 0

    failed_knowledge_docs = (
        await db.execute(
            select(func.count(KnowledgeDocument.id)).where(
                KnowledgeDocument.status == DocumentStatus.FAILED.value
            )
        )
    ).scalar() or 0

    today_pv = (
        await db.execute(select(func.count(PageView.id)).where(PageView.created_at >= today))
    ).scalar() or 0

    today_uv = (
        await db.execute(
            select(func.count(func.distinct(PageView.visitor_id))).where(
                PageView.created_at >= today
            )
        )
    ).scalar() or 0

    since_7d = today - timedelta(days=7)
    recent_errors = (
        await db.execute(
            select(func.count(ErrorEntry.id)).where(ErrorEntry.created_at >= since_7d)
        )
    ).scalar() or 0

    # 近 7 天新增用户趋势
    new_users_trend_result = await db.execute(
        select(
            func.date(User.created_at).label("day"),
            func.count(User.id).label("count"),
        )
        .where(User.created_at >= since_7d)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    newUsersTrend = [
        {"date": str(row.day), "count": row.count} for row in new_users_trend_result.all()
    ]

    pv_trend_result = await db.execute(
        select(
            func.date(PageView.created_at).label("day"),
            func.count(PageView.id).label("count"),
        )
        .where(PageView.created_at >= since_7d)
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
    )
    pvTrend = [{"date": str(row.day), "count": row.count} for row in pv_trend_result.all()]

    return {
        "userCount": user_count,
        "todayNewUsers": today_new_users,
        "courseCount": course_count,
        "todayOrders": today_orders,
        "totalRevenue": round(total_revenue, 2),
        "todayRevenue": round(today_revenue, 2),
        "knowledgeDocCount": knowledge_doc_count,
        "knowledgeReadyCount": knowledge_ready_count,
        "unpaidOrders": unpaid_orders,
        "failedKnowledgeDocs": failed_knowledge_docs,
        "todayPv": today_pv,
        "todayUv": today_uv,
        "recentErrors": recent_errors,
        "newUsersTrend": newUsersTrend,
        "pvTrend": pvTrend,
    }

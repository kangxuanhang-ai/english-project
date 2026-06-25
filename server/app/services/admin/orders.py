"""B 端订单管理"""
import csv
from datetime import datetime, timezone
from io import StringIO
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.course import CourseRecord
from app.models.payment import PaymentRecord, TradeStatus
from app.models.user import User

TRADE_STATUS_LABELS = {
    "NOT_PAY": "未支付",
    "WAIT_BUYER_PAY": "待支付",
    "TRADE_CLOSED": "已关闭",
    "TRADE_SUCCESS": "支付成功",
    "TRADE_FINISHED": "已完成",
}
EXPORT_LIMIT = 5000
CN_TZ = ZoneInfo("Asia/Shanghai")


def _format_cn_time(iso: str | None) -> str:
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CN_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _apply_order_filters(
    query,
    count_query,
    *,
    status: str | None,
    start_date: str | None,
    end_date: str | None,
    keyword: str | None,
):
    if status == "UNPAID":
        cond = PaymentRecord.trade_status.in_([TradeStatus.NOT_PAY, TradeStatus.WAIT_BUYER_PAY])
        query = query.where(cond)
        count_query = count_query.where(cond)
    elif status:
        try:
            trade_status = TradeStatus(status)
            query = query.where(PaymentRecord.trade_status == trade_status)
            count_query = count_query.where(PaymentRecord.trade_status == trade_status)
        except ValueError:
            pass

    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.where(PaymentRecord.created_at >= start)
        count_query = count_query.where(PaymentRecord.created_at >= start)

    if end_date:
        end = datetime.fromisoformat(end_date)
        query = query.where(PaymentRecord.created_at <= end)
        count_query = count_query.where(PaymentRecord.created_at <= end)

    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        cond = or_(PaymentRecord.out_trade_no.ilike(kw), User.name.ilike(kw))
        query = query.where(cond)
        count_query = count_query.where(cond)

    return query, count_query


def _order_item(record: PaymentRecord, user: User | None = None) -> dict:
    return {
        "id": record.id,
        "outTradeNo": record.out_trade_no,
        "tradeNo": record.trade_no,
        "amount": float(record.amount),
        "subject": record.subject,
        "tradeStatus": record.trade_status.value,
        "sendPayTime": record.send_pay_time.isoformat() if record.send_pay_time else None,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
        "userId": record.user_id,
        "userName": user.name if user else None,
        "userPhone": user.phone if user else None,
    }


async def list_orders(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 10,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
) -> dict:
    query = select(PaymentRecord, User).join(User, User.id == PaymentRecord.user_id)
    count_query = select(func.count(PaymentRecord.id)).join(
        User, User.id == PaymentRecord.user_id
    )

    query, count_query = _apply_order_filters(
        query,
        count_query,
        status=status,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
    )

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(PaymentRecord.created_at.desc()).offset(offset).limit(page_size)
    )

    items = [_order_item(record, user) for record, user in result.all()]
    return {"list": items, "total": total}


async def get_order_detail(db: AsyncSession, order_id: str) -> dict | None:
    result = await db.execute(
        select(PaymentRecord)
        .options(
            joinedload(PaymentRecord.user),
            joinedload(PaymentRecord.course_records).joinedload(CourseRecord.course),
        )
        .where(PaymentRecord.id == order_id)
    )
    record = result.unique().scalar_one_or_none()
    if not record:
        return None

    courses = []
    for cr in record.course_records:
        if cr.course:
            c = cr.course
            courses.append({"id": c.id, "name": c.name, "value": c.value})

    data = _order_item(record, record.user)
    data["body"] = record.body
    data["courses"] = courses
    return data


async def export_orders_csv(
    db: AsyncSession,
    *,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
) -> str:
    query = select(PaymentRecord, User).join(User, User.id == PaymentRecord.user_id)
    count_query = select(func.count(PaymentRecord.id)).join(
        User, User.id == PaymentRecord.user_id
    )
    query, _ = _apply_order_filters(
        query,
        count_query,
        status=status,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
    )
    result = await db.execute(
        query.order_by(PaymentRecord.created_at.desc()).limit(EXPORT_LIMIT)
    )

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["订单号", "用户", "手机号", "金额", "状态", "创建时间"])
    for record, user in result.all():
        item = _order_item(record, user)
        writer.writerow([
            item["outTradeNo"],
            item["userName"] or "",
            item["userPhone"] or "",
            f"{item['amount']:.2f}",
            TRADE_STATUS_LABELS.get(item["tradeStatus"], item["tradeStatus"]),
            _format_cn_time(item["createdAt"]),
        ])
    return "\ufeff" + buf.getvalue()

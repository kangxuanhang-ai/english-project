import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from nanoid import generate

from app.models.payment import PaymentRecord, TradeStatus
from app.models.course import CourseRecord
from app.services.socket import emit_payment_success
from app.config import settings
from shared.alipay_client import alipay_client


def create_trade_no() -> str:
    """生成订单号，格式 XM-<nanoid>"""
    return f"XM-{generate(size=12)}"


def _parse_amount(value) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _amounts_match(expected: Decimal, received) -> bool:
    parsed = _parse_amount(received)
    if parsed is None:
        return False
    return parsed == expected


async def _find_pending_payment(
    db: AsyncSession, user_id: str, course_id: str
) -> PaymentRecord | None:
    """查找同一用户+课程未完成的 pending 订单（5 分钟内）。"""
    cutoff = datetime.now() - timedelta(minutes=5)
    result = await db.execute(
        select(PaymentRecord).where(
            PaymentRecord.user_id == user_id,
            PaymentRecord.trade_status.in_(
                [TradeStatus.NOT_PAY, TradeStatus.WAIT_BUYER_PAY]
            ),
            PaymentRecord.created_at >= cutoff,
        )
    )
    for payment in result.scalars():
        body = _parse_payment_body(payment.body)
        if body and body.get("courseId") == course_id:
            return payment
    return None


def _build_alipay_page_url(
    *,
    out_trade_no: str,
    total_amount: Decimal,
    subject: str,
    pay_body: str,
    time_expire: datetime,
) -> str:
    from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
    from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest

    model = AlipayTradePagePayModel()
    model.out_trade_no = out_trade_no
    model.total_amount = str(total_amount)
    model.subject = subject
    model.body = pay_body
    model.product_code = "FAST_INSTANT_TRADE_PAY"
    model.time_expire = time_expire.strftime("%Y-%m-%d %H:%M:%S")

    request = AlipayTradePagePayRequest(biz_model=model)
    request.notify_url = f"{settings.alipay_notify_url}/api/v1/pay/notify"
    request.return_url = settings.alipay_return_url

    return alipay_client.get_client().page_execute(request, http_method="GET")


async def create_payment(db: AsyncSession, data: dict, user_id: str) -> dict:
    """
    创建支付订单。
    对应 NestJS PayService.create。
    """
    from app.models.course import Course

    # 检查是否已购买
    existing = await db.execute(
        select(CourseRecord).where(
            CourseRecord.user_id == user_id,
            CourseRecord.course_id == data["courseId"],
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("您已经购买过该课程")

    # 校验支付金额与课程实际价格一致（防止前端篡改金额）
    course_result = await db.execute(
        select(Course).where(Course.id == data["courseId"])
    )
    course = course_result.scalar_one_or_none()
    if not course:
        raise ValueError("课程不存在")

    total_amount = _parse_amount(data["total_amount"])
    if total_amount is None or course.price != total_amount:
        raise ValueError("支付金额与课程价格不一致")

    pending = await _find_pending_payment(db, user_id, data["courseId"])
    if pending:
        raise ValueError("您有未完成的支付订单，请完成支付或稍后再试")

    # 创建支付记录（body 存 courseId/userId JSON，供回调与主动查询使用）
    out_trade_no = create_trade_no()
    pay_body = json.dumps({"courseId": data["courseId"], "userId": user_id})
    payment = PaymentRecord(
        id=generate(size=20),
        user_id=user_id,
        out_trade_no=out_trade_no,
        amount=total_amount,
        subject=data["subject"],
        body=pay_body,
    )
    db.add(payment)
    await db.flush()
    await db.commit()
    await db.refresh(payment)

    # 生成支付宝支付 URL
    time_expire = datetime.now() + timedelta(minutes=5)

    pay_url = _build_alipay_page_url(
        out_trade_no=out_trade_no,
        total_amount=total_amount,
        subject=data["subject"],
        pay_body=pay_body,
        time_expire=time_expire,
    )

    return {
        "payUrl": pay_url,
        "outTradeNo": out_trade_no,
        "timeExpire": int(time_expire.timestamp() * 1000),
    }


async def resume_payment(db: AsyncSession, user_id: str, course_id: str) -> dict:
    """为 pending 订单重新生成支付 URL（同一 out_trade_no）。"""
    pending = await _find_pending_payment(db, user_id, course_id)
    if not pending:
        raise ValueError("无待支付订单，请重新购买")

    time_expire = datetime.now() + timedelta(minutes=5)
    pay_url = _build_alipay_page_url(
        out_trade_no=pending.out_trade_no,
        total_amount=pending.amount,
        subject=pending.subject,
        pay_body=pending.body or "",
        time_expire=time_expire,
    )

    return {
        "payUrl": pay_url,
        "outTradeNo": pending.out_trade_no,
        "timeExpire": int(time_expire.timestamp() * 1000),
    }


def _verify_alipay_sign(data: dict, sign: str) -> bool:
    """验证支付宝 RSA2 签名"""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, utils
        from alipay.aop.api.util.SignatureUtils import fill_public_key_marker
        import base64

        # 拼接待验签字符串（按 key 排序，排除 sign 和 sign_type）
        verify_data = {k: v for k, v in data.items() if k not in ("sign", "sign_type")}
        sign_content = "&".join(f"{k}={v}" for k, v in sorted(verify_data.items()))

        # 加载支付宝公钥
        pub_pem = fill_public_key_marker(settings.alipay_public_key)
        if not pub_pem.startswith("-----"):
            lines = [pub_pem[i:i+64] for i in range(0, len(pub_pem), 64)]
            pub_pem = f"-----BEGIN PUBLIC KEY-----\n" + "\n".join(lines) + "\n-----END PUBLIC KEY-----\n"
        public_key = serialization.load_pem_public_key(pub_pem.encode())

        # RSA2 = SHA256WithRSA
        signature = base64.b64decode(sign)
        public_key.verify(
            signature,
            sign_content.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception as e:
        logging.warning(f"Signature verification failed: {e}")
        return False


def _parse_payment_body(body_str: str | None) -> dict | None:
    """解析订单 body 中的 courseId / userId"""
    if not body_str:
        return None
    try:
        body = json.loads(body_str)
    except (json.JSONDecodeError, TypeError) as e:
        logging.warning(f"Failed to parse payment body: {e}")
        return None
    if not body.get("courseId") or not body.get("userId"):
        return None
    return body


def query_alipay_trade(out_trade_no: str) -> dict | None:
    """向支付宝查询订单状态（notify 未到达时的补偿）"""
    from alipay.aop.api.domain.AlipayTradeQueryModel import AlipayTradeQueryModel
    from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest

    model = AlipayTradeQueryModel()
    model.out_trade_no = out_trade_no
    request = AlipayTradeQueryRequest(biz_model=model)
    try:
        response_str = alipay_client.get_client().execute(request)
        if isinstance(response_str, bytes):
            response_str = response_str.decode("utf-8")
        data = json.loads(response_str)
    except Exception as e:
        logging.warning(f"Alipay trade query failed: {e}")
        return None

    if data.get("code") != "10000":
        logging.info(f"Alipay trade query not ready: {data.get('sub_msg') or data.get('msg')}")
        return None
    return data


async def _fulfill_payment(
    db: AsyncSession,
    payment: PaymentRecord,
    trade_no: str | None,
    body: dict,
    *,
    notify_socket: bool = True,
) -> bool:
    """将已支付订单落库并开通课程（幂等）"""
    if body.get("userId") != payment.user_id:
        logging.warning(
            f"userId mismatch: body={body.get('userId')} payment={payment.user_id}"
        )
        return False

    if payment.trade_status == TradeStatus.TRADE_SUCCESS:
        return True

    existing_record = await db.execute(
        select(CourseRecord).where(
            CourseRecord.user_id == body["userId"],
            CourseRecord.course_id == body["courseId"],
        )
    )
    if existing_record.scalar_one_or_none():
        payment.trade_no = trade_no
        payment.trade_status = TradeStatus.TRADE_SUCCESS
        payment.send_pay_time = datetime.now()
        await db.commit()
        return True

    payment.trade_no = trade_no
    payment.trade_status = TradeStatus.TRADE_SUCCESS
    payment.send_pay_time = datetime.now()
    await db.flush()

    course_record = CourseRecord(
        id=generate(size=20),
        user_id=body["userId"],
        course_id=body["courseId"],
        is_purchased=True,
        payment_record_id=payment.id,
    )
    db.add(course_record)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logging.info(
            f"Duplicate course record for {body['userId']}/{body['courseId']}, treating as success"
        )
        return True

    if notify_socket:
        await emit_payment_success(
            body["userId"],
            body["courseId"],
            payment.out_trade_no,
        )
    return True


async def handle_payment_notify(db: AsyncSession, form_data: dict) -> bool:
    """
    处理支付宝回调。
    对应 NestJS PayService.notify。
    """
    logging.info(f"Alipay notify received: out_trade_no={form_data.get('out_trade_no')}")

    # 验证支付宝签名（防止伪造回调）
    sign = form_data.get("sign", "")
    if not _verify_alipay_sign(form_data, sign):
        logging.warning("Alipay signature verification failed")
        return False

    out_trade_no = form_data.get("out_trade_no")
    trade_no = form_data.get("trade_no")
    body_str = form_data.get("body") or "{}"

    result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.out_trade_no == out_trade_no)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        return False

    if payment.trade_status == TradeStatus.TRADE_SUCCESS:
        return True

    if form_data.get("trade_status") != "TRADE_SUCCESS":
        logging.info(f"Ignore non-success trade_status: {form_data.get('trade_status')}")
        return False

    if not _amounts_match(payment.amount, form_data.get("total_amount")):
        logging.warning(
            f"Amount mismatch on notify: payment={payment.amount} callback={form_data.get('total_amount')}"
        )
        return False

    body = _parse_payment_body(body_str) or _parse_payment_body(payment.body)
    if not body:
        await db.rollback()
        return False

    return await _fulfill_payment(db, payment, trade_no, body)


async def sync_payment_status(
    db: AsyncSession, out_trade_no: str, user_id: str
) -> dict:
    """
    主动同步支付状态。
    本地开发时 ngrok 回调常失败，前端轮询此接口完成购课。
    """
    result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.out_trade_no == out_trade_no)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise ValueError("订单不存在")
    if payment.user_id != user_id:
        raise ValueError("无权查询该订单")

    if payment.trade_status == TradeStatus.TRADE_SUCCESS:
        return {"paid": True}

    alipay_data = query_alipay_trade(out_trade_no)
    if not alipay_data:
        return {"paid": False}

    trade_status = alipay_data.get("trade_status")
    if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        return {"paid": False, "tradeStatus": trade_status}

    if not _amounts_match(payment.amount, alipay_data.get("total_amount")):
        logging.warning(
            f"Amount mismatch on sync: payment={payment.amount} alipay={alipay_data.get('total_amount')}"
        )
        raise ValueError("支付金额与订单不一致，已拒绝开通课程")

    body = _parse_payment_body(alipay_data.get("body")) or _parse_payment_body(
        payment.body
    )
    if not body:
        raise ValueError("订单附加信息异常，无法开通课程")

    paid = await _fulfill_payment(
        db,
        payment,
        alipay_data.get("trade_no"),
        body,
        notify_socket=True,
    )
    return {"paid": paid}

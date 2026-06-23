import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
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
    if float(course.price) != float(data["total_amount"]):
        raise ValueError("支付金额与课程价格不一致")

    # 创建支付记录
    out_trade_no = create_trade_no()
    payment = PaymentRecord(
        id=generate(size=20),
        user_id=user_id,
        out_trade_no=out_trade_no,
        amount=data["total_amount"],
        subject=data["subject"],
        body=data["body"],
    )
    db.add(payment)
    await db.flush()
    await db.commit()
    await db.refresh(payment)

    # 生成支付宝支付 URL
    time_expire = datetime.now() + timedelta(minutes=1)  # 使用本地时间（CST），支付宝以中国时区为准

    from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
    from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest

    model = AlipayTradePagePayModel()
    model.out_trade_no = out_trade_no
    model.total_amount = str(data["total_amount"])
    model.subject = data["subject"]
    model.body = json.dumps({"courseId": data["courseId"], "userId": user_id})
    model.product_code = "FAST_INSTANT_TRADE_PAY"
    model.time_expire = time_expire.strftime("%Y-%m-%d %H:%M:%S")

    request = AlipayTradePagePayRequest(biz_model=model)
    request.notify_url = f"{settings.alipay_notify_url}/api/v1/pay/notify"
    request.return_url = settings.alipay_return_url

    pay_url = alipay_client.get_client().page_execute(request, http_method="GET")

    return {
        "payUrl": pay_url,
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


async def handle_payment_notify(db: AsyncSession, form_data: dict) -> bool:
    """
    处理支付宝回调。
    对应 NestJS PayService.notify。
    """
    # 验证支付宝签名（防止伪造回调）
    sign = form_data.get("sign", "")
    if not _verify_alipay_sign(form_data, sign):
        logging.warning("Alipay signature verification failed")
        return False

    out_trade_no = form_data.get("out_trade_no")
    trade_no = form_data.get("trade_no")
    body_str = form_data.get("body", "{}")

    # 更新支付记录
    result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.out_trade_no == out_trade_no)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        return False

    payment.trade_no = trade_no
    payment.trade_status = TradeStatus.TRADE_SUCCESS
    payment.send_pay_time = datetime.now()
    await db.flush()

    # 创建课程记录（带 JSON 解析异常处理）
    try:
        body = json.loads(body_str)
    except (json.JSONDecodeError, TypeError) as e:
        logging.warning(f"Failed to parse payment body: {e}")
        await db.rollback()  # 回滚，避免支付成功但无课程记录的不一致状态
        return False

    course_record = CourseRecord(
        id=generate(size=20),
        user_id=body["userId"],
        course_id=body["courseId"],
        is_purchased=True,
        payment_record_id=payment.id,
    )
    db.add(course_record)
    await db.flush()
    await db.commit()
    await db.refresh(payment)
    await db.refresh(course_record)

    # Socket.IO 通知前端
    await emit_payment_success(body["userId"])

    return True

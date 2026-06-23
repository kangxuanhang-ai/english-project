import logging
import socketio

from app.config import settings
from app.services.auth import verify_token

# 创建 Socket.IO 服务（asyncio 模式，兼容客户端 v4/v5）
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=settings.cors_origins)


@sio.event
async def connect(sid, environ):
    """客户端连接时通过 JWT 鉴权，验证后加入用户房间"""
    from urllib.parse import parse_qs

    query = parse_qs(environ.get("QUERY_STRING", ""))
    token = query.get("token", [None])[0]
    if not token:
        raise ConnectionRefusedError("缺少认证 token")
    try:
        payload = verify_token(token)
        user_id = payload["userId"]
    except Exception:
        raise ConnectionRefusedError("认证失败")
    await sio.enter_room(sid, f"user_{user_id}")
    logging.info(f"Socket.IO: user_{user_id} connected")


@sio.event
async def disconnect(sid):
    """客户端断开连接"""
    pass


async def emit_payment_success(user_id: str):
    """
    向指定用户发送支付成功通知。
    对应 NestJS SocketGateway.emitPaymentSuccess。
    """
    await sio.emit("paymentSuccess", user_id, room=f"user_{user_id}")

import json
import logging
from datetime import datetime

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def transform_bigint(obj):
    """将 bigint 转换为字符串，保留 Date 类型不变（Python 无 bigint 问题，但保持接口一致）"""
    if isinstance(obj, list):
        return [transform_bigint(item) for item in obj]
    if isinstance(obj, dict):
        return {key: transform_bigint(value) for key, value in obj.items()}
    return obj


async def response_envelope_middleware(request: Request, call_next):
    """全局响应信封中间件：包装所有成功响应为统一格式"""
    # 跳过 Socket.IO 路径（WebSocket 握手不能被拦截）
    if request.url.path.startswith("/socket.io"):
        return await call_next(request)

    # 跳过 SSE 流式响应路径（流式响应不能被读取和包装）
    if request.url.path.startswith("/ai/v1/chat"):
        return await call_next(request)

    # 跳过支付宝回调（需要返回纯文本 "success"，不能被包装成 JSON）
    if request.url.path.startswith("/api/v1/pay/notify"):
        return await call_next(request)

    # 跳过 CSV 导出（非 JSON；且 body 读取后不能原样 return response）
    if request.url.path.startswith("/api/v1/admin/orders/export"):
        return await call_next(request)

    response = await call_next(request)

    # 只处理 JSON 响应（2xx 状态码）
    if response.status_code >= 200 and response.status_code < 300:
        # 读取原始响应体
        body = b""
        async for chunk in response.body_iterator:
            body += chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")

        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return response

        # 如果已经是信封格式（有 code 和 data 字段），直接包装
        if isinstance(data, dict) and "code" in data and "data" in data:
            envelope = {
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "message": data.get("message", "请求成功"),
                "code": data.get("code", 200),
                "success": True,
                "data": transform_bigint(data.get("data")),
            }
        else:
            # 普通响应，直接包装
            envelope = {
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "message": "请求成功",
                "code": 200,
                "success": True,
                "data": transform_bigint(data),
            }

        return JSONResponse(content=envelope, status_code=response.status_code)

    return response


async def exception_handler(request: Request, exc):
    """全局异常处理器：统一错误响应格式"""
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "message": str(exc.detail),
                "code": exc.status_code,
                "success": False,
            },
        )

    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "message": "请求参数验证失败",
                "code": 422,
                "success": False,
            },
        )

    # 未知异常（不暴露内部信息）
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
            "message": "服务器内部错误",
            "code": 500,
            "success": False,
        },
    )

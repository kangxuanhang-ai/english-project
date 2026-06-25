"""AI 服务速率限制（JWT 校验 userId + 可配置 storage）"""
from fastapi import Request
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.services.auth import ALGORITHM


def _get_user_id_from_request(request: Request) -> str:
    """从已签名的 JWT 提取 userId，失败则回退 IP。"""
    try:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return get_remote_address(request)
        token = auth.split(" ", 1)[1]
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload.get("userId") or get_remote_address(request)
    except (JWTError, IndexError, TypeError):
        return get_remote_address(request)


def create_limiter() -> Limiter:
    from ai.config import ai_settings

    kwargs: dict = {"key_func": _get_user_id_from_request}
    if ai_settings.rate_limit_storage_uri:
        kwargs["storage_uri"] = ai_settings.rate_limit_storage_uri
    return Limiter(**kwargs)


limiter = create_limiter()

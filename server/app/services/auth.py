from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"


def create_access_token(payload: dict) -> str:
    """生成 access token（15分钟过期）"""
    to_encode = {**payload, "tokenType": "access"}
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(payload: dict) -> str:
    """生成 refresh token（7 天过期）"""
    to_encode = {**payload, "tokenType": "refresh"}
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def generate_tokens(payload: dict) -> dict:
    """生成 access + refresh token 对（对应 NestJS AuthService.generateToken）"""
    return {
        "accessToken": create_access_token(payload),
        "refreshToken": create_refresh_token(payload),
    }


def verify_token(token: str, expected_type: str = "access") -> dict:
    """验证 JWT token，返回 payload。tokenType 不匹配时抛异常。"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("tokenType") != expected_type:
            raise ValueError(f"Invalid token type: expected {expected_type}")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")

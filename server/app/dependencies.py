from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth import verify_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI 依赖注入：验证 access token 并返回用户 payload。
    对应 NestJS 的 AuthGuard。
    """
    token = credentials.credentials
    try:
        payload = verify_token(token, expected_type="access")
        return payload
    except ValueError:
        raise HTTPException(status_code=401, detail="token已过期或无效")


async def get_current_user_optional(
    request: Request,
) -> dict | None:
    """可选认证：有 token 则验证，没有则返回 None"""
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    try:
        token = auth.split(" ")[1]
        return verify_token(token, expected_type="access")
    except (ValueError, IndexError):
        return None


async def get_current_admin(
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """管理员鉴权：JWT 有效且 user.role == admin"""
    result = await db.execute(select(User.role).where(User.id == payload["userId"]))
    role = result.scalar_one_or_none()
    if role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return payload

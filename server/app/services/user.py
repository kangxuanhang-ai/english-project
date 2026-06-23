import re
import time
from datetime import UTC, date, datetime
from io import BytesIO

import bcrypt
from nanoid import generate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.services.auth import generate_tokens, verify_token
from shared.minio_client import minio_client

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def user_to_response(user: User, token: dict) -> dict:
    """将 User ORM 对象转为 API 响应格式（排除 password）"""
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "address": user.address,
        "avatar": user.avatar,
        "bio": user.bio,
        "isTimingTask": user.is_timing_task,
        "timingTaskTime": user.timing_task_time,
        "wordNumber": user.word_number,
        "dayNumber": user.day_number,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "updatedAt": user.updated_at.isoformat() if user.updated_at else None,
        "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at else None,
        "token": token,
    }


async def register_user(db: AsyncSession, data: dict) -> dict:
    """
    用户注册。
    对应 NestJS UserController.register。
    """
    # 检查手机号是否已注册
    existing = await db.execute(select(User).where(User.phone == data["phone"]))
    if existing.scalar_one_or_none():
        raise ValueError("手机号已注册")

    # 检查邮箱是否已注册（如果提供了邮箱）
    if data.get("email"):
        email_existing = await db.execute(select(User).where(User.email == data["email"]))
        if email_existing.scalar_one_or_none():
            raise ValueError("邮箱已注册")

    # 创建用户（前端已 MD5 哈希，服务端再加一层 bcrypt）
    md5_hash = data["password"]
    hashed = bcrypt.hashpw(md5_hash.encode(), bcrypt.gensalt()).decode()
    user = User(
        id=generate(size=20),
        name=data["name"],
        phone=data["phone"],
        email=data.get("email"),
        password=hashed,
    )
    db.add(user)
    await db.flush()  # 获取 ID
    await db.commit()  # 显式提交（get_db 不自动 commit）
    await db.refresh(user)  # 刷新对象，确保属性可访问

    # 生成 token
    token = generate_tokens({"userId": user.id, "name": user.name, "email": user.email})

    return user_to_response(user, token)


async def login_user(db: AsyncSession, data: dict) -> dict:
    """
    用户登录。
    对应 NestJS UserController.login。
    """
    # 查找用户
    result = await db.execute(select(User).where(User.phone == data["phone"]))
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError("手机号未注册")

    # 验证密码（兼容 bcrypt 和旧 MD5，首次 MD5 登录成功后静默升级）
    md5_hash = data["password"]

    if user.password.startswith("$2b$"):
        # 已迁移用户，bcrypt 验证
        if not bcrypt.checkpw(md5_hash.encode(), user.password.encode()):
            raise ValueError("密码错误")
    else:
        # 未迁移用户，MD5 直接比较
        if user.password != md5_hash:
            raise ValueError("密码错误")
        # 首次登录成功后静默升级为 bcrypt
        user.password = bcrypt.hashpw(md5_hash.encode(), bcrypt.gensalt()).decode()

    # 更新最后登录时间
    user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
    await db.flush()
    await db.commit()
    await db.refresh(user)  # 刷新对象，确保属性可访问

    # 生成 token
    token = generate_tokens({"userId": user.id, "name": user.name, "email": user.email})

    return user_to_response(user, token)


async def refresh_user_token(db: AsyncSession, token: str) -> dict:
    """
    刷新 token。
    对应 NestJS UserService.refreshToken。
    """
    try:
        payload = verify_token(token, expected_type="refresh")
    except ValueError:
        raise ValueError("refreshToken已过期或无效")

    # 查找用户
    result = await db.execute(select(User).where(User.id == payload["userId"]))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("用户不存在")

    # 生成新 token
    new_token = generate_tokens({"userId": user.id, "name": user.name, "email": user.email})
    return new_token


async def upload_avatar(file) -> dict:
    """
    上传头像到 MinIO。
    对应 NestJS UserService.uploadAvatar。
    """
    if not file:
        raise ValueError("文件不存在")

    # Content-type 校验
    if file.content_type not in ALLOWED_TYPES:
        raise ValueError("仅支持 JPG/PNG/WebP 格式")

    content = await file.read()
    if len(content) > 1024 * 1024 * 5:
        raise ValueError("文件大小不能超过5MB")

    client = minio_client.get_client()
    bucket = minio_client.get_bucket()

    # 文件名校验（去掉路径分隔符）
    safe_name = re.sub(r'[^\w.\-]', '_', file.filename or "avatar.png")
    file_name = f"{int(time.time() * 1000)}-{safe_name}"

    # 上传到 MinIO
    client.put_object(
        bucket,
        file_name,
        BytesIO(content),
        length=len(content),
        content_type=file.content_type,
    )

    # 生成 URL
    protocol = "https" if settings.minio_use_ssl else "http"
    object_path = f"/{bucket}/{file_name}"
    preview_url = f"{protocol}://{settings.minio_endpoint}:{settings.minio_port}{object_path}"

    return {"previewUrl": preview_url, "databaseUrl": object_path}


async def update_user(db: AsyncSession, user_id: str, data: dict) -> dict:
    """
    更新用户信息。
    对应 NestJS UserService.updateUser。
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("用户不存在")

    # 更新字段（只更新非 None 的字段）
    for key, value in data.items():
        if value is not None:
            # 转换 camelCase → snake_case
            snake_key = "".join(
                ["_" + c.lower() if c.isupper() else c for c in key]
            ).lstrip("_")
            if hasattr(user, snake_key):
                setattr(user, snake_key, value)

    await db.flush()
    await db.commit()
    await db.refresh(user)

    return {
        "name": user.name,
        "email": user.email,
        "address": user.address,
        "avatar": user.avatar,
        "bio": user.bio,
        "isTimingTask": user.is_timing_task,
        "timingTaskTime": user.timing_task_time,
    }


async def check_in(db: AsyncSession, user_id: str) -> dict:
    """
    用户每日打卡。
    如果今天已打卡，返回当前 day_number。
    如果今天未打卡，day_number += 1。
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("用户不存在")

    now_utc = datetime.now(UTC)
    today = now_utc.date()
    # last_check_in_at 记录最后打卡时间（UTC）
    already_checked = user.last_check_in_at and user.last_check_in_at.date() == today

    if already_checked:
        return {"dayNumber": user.day_number, "checkedIn": False}

    user.day_number = (user.day_number or 0) + 1
    user.last_check_in_at = now_utc.replace(tzinfo=None)
    await db.commit()
    await db.refresh(user)
    return {"dayNumber": user.day_number, "checkedIn": True}

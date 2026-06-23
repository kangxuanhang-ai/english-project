from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import UserLogin, UserRegister, UserUpdate
from app.services.user import login_user, register_user, refresh_user_token, upload_avatar, update_user, check_in as check_in_user

router = APIRouter(prefix="/api/v1/user", tags=["user"])


@router.post("/register")
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    用户注册。
    对应 NestJS POST /api/v1/user/register。
    """
    try:
        result = await register_user(db, data.model_dump())
        return {"data": result, "code": 200, "message": "注册成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    用户登录。
    对应 NestJS POST /api/v1/user/login。
    """
    try:
        result = await login_user(db, data.model_dump())
        return {"data": result, "code": 200, "message": "登录成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh-token")
async def refresh(data: dict, db: AsyncSession = Depends(get_db)):
    """刷新 token。对应 NestJS POST /api/v1/user/refresh-token"""
    try:
        result = await refresh_user_token(db, data.get("refreshToken", ""))
        return {"data": result, "code": 200, "message": "刷新成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload-avatar")
async def upload(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    """上传头像。添加鉴权，防止匿名上传"""
    try:
        result = await upload_avatar(file)
        return {"data": result, "code": 200, "message": "上传成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/update-user")
async def update(data: UserUpdate, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """更新用户信息。对应 NestJS POST /api/v1/user/update-user（需要认证）"""
    try:
        result = await update_user(db, user["userId"], data.model_dump(exclude_none=True))
        return {"data": result, "code": 200, "message": "更新成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/check-in")
async def check_in(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """每日打卡。"""
    try:
        result = await check_in_user(db, user["userId"])
        message = "打卡成功" if result["checkedIn"] else "今日已打卡"
        return {"data": result, "code": 200, "message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

from pydantic import BaseModel, Field


class UserLogin(BaseModel):
    phone: str
    password: str


class UserRegister(BaseModel):
    name: str
    phone: str
    email: str | None = None
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    address: str | None = None
    avatar: str | None = None
    bio: str | None = None
    isTimingTask: bool | None = None
    timingTaskTime: str | None = None


class RefreshTokenRequest(BaseModel):
    refreshToken: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str | None = None
    phone: str
    address: str | None = None
    avatar: str | None = None
    bio: str | None = None
    isTimingTask: bool = False
    timingTaskTime: str = "00:00:00"
    wordNumber: int = 0
    dayNumber: int = 0
    createdAt: str | None = None
    updatedAt: str | None = None
    lastLoginAt: str | None = None
    token: TokenResponse

    class Config:
        from_attributes = True

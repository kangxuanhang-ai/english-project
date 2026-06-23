import logging
import socketio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.middleware import response_envelope_middleware, exception_handler
from app.rate_limit import limiter
from app.routers import user, word_book, course, pay, learn, tracker
from app.services.socket import sio


@asynccontextmanager
async def lifespan(app):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    yield


app = FastAPI(title="English Server", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 注册全局中间件
app.middleware("http")(response_envelope_middleware)

# 注册全局异常处理器
app.add_exception_handler(StarletteHTTPException, exception_handler)
app.add_exception_handler(RequestValidationError, exception_handler)

# 注册路由
app.include_router(user.router)
app.include_router(word_book.router)
app.include_router(course.router)
app.include_router(pay.router)
app.include_router(learn.router)
app.include_router(tracker.router)


@app.get("/")
async def root():
    return {"message": "access success"}


# 挂载 Socket.IO（必须在路由之后）
socket_app = socketio.ASGIApp(sio, app)

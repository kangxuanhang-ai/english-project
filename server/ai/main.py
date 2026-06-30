import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

# Windows 上 psycopg 需要 SelectorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

from ai.routers import prompt, chat, conversation, recommend
from ai.services.digest import start_scheduler
from ai.services.tracing import configure_langsmith_tracing
from ai.services.wordbook_short_circuit import WORDBOOK_FEATURE
from app.config import settings
from app.middleware import response_envelope_middleware, exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动定时任务"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    configure_langsmith_tracing()
    logging.getLogger(__name__).info("AI chat: wordbook short-circuit v3 enabled (router intercept)")
    start_scheduler()
    yield
    from ai.services.chat import reset_checkpointer
    from ai.services.llm import close_http_client
    from ai.services.recommend_cache import close_recommend_cache

    await reset_checkpointer()
    await close_http_client()
    await close_recommend_cache()


ai_app = FastAPI(title="English AI Server", version="0.1.0", lifespan=lifespan)

ai_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册中间件（跳过 SSE 和 Socket.IO 路径）
ai_app.middleware("http")(response_envelope_middleware)
ai_app.add_exception_handler(StarletteHTTPException, exception_handler)
ai_app.add_exception_handler(RequestValidationError, exception_handler)

from ai.rate_limit import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

ai_app.state.limiter = limiter
ai_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 注册路由
ai_app.include_router(prompt.router)
ai_app.include_router(chat.router)
ai_app.include_router(conversation.router)
ai_app.include_router(recommend.router)


@ai_app.get("/health")
async def health():
    return {"status": "ok", "wordbook": WORDBOOK_FEATURE}


@ai_app.get("/")
async def root():
    return {"message": "ai access success"}

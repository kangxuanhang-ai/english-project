import logging
import socketio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import async_session
from app.middleware import response_envelope_middleware, exception_handler
from app.rate_limit import limiter
from app.routers import user, word_book, course, pay, learn, tracker
from app.routers.admin import router as admin_router
from app.services.socket import sio
from shared.minio_client import minio_client

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await minio_client.init_bucket()
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
app.add_exception_handler(StarletteHTTPException, exception_handler)
app.add_exception_handler(RequestValidationError, exception_handler)
app.add_exception_handler(Exception, exception_handler)

app.middleware("http")(response_envelope_middleware)

app.include_router(user.router)
app.include_router(word_book.router)
app.include_router(course.router)
app.include_router(pay.router)
app.include_router(learn.router)
app.include_router(tracker.router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"message": "access success"}


@app.get("/health")
async def health():
    """存活探针 + 数据库连通性"""
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "up"}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "down"},
        )


socket_app = socketio.ASGIApp(sio, app)

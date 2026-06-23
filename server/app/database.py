from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# async engine — 使用 asyncpg 驱动
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,    # 1小时后回收空闲连接，防止连接过期
    pool_pre_ping=True,   # 使用前检查连接健康，避免使用失效连接
)

# Session 工厂
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI 依赖注入：获取数据库 session。
    注意：不在这里自动 commit，由各 service 函数显式调用 await db.commit()。
    这与 NestJS 版 PrismaService 的行为一致（每次操作原子性）。
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import normalize_database_url

engine = None
async_session: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str, *, pool_size: int = 5, max_overflow: int = 10) -> None:
    global engine, async_session
    url = normalize_database_url(database_url)
    engine = create_async_engine(
        url,
        echo=False,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)


async def dispose_db() -> None:
    global engine, async_session
    if engine is not None:
        await engine.dispose()
    engine = None
    async_session = None

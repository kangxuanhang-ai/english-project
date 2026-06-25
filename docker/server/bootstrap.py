"""确保 langchain 库存在（compose 无 init 脚本卷时仍可首次部署）。"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import normalize_database_url


async def main() -> None:
    base_url = normalize_database_url(settings.database_url)
    maintenance_url = f"{base_url.rsplit('/', 1)[0]}/postgres"
    engine = create_async_engine(maintenance_url)
    try:
        async with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
            exists = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'langchain'")
            )
            if not exists.scalar():
                await conn.execute(text("CREATE DATABASE langchain"))
                print("Created database langchain")
            else:
                print("Database langchain already exists")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

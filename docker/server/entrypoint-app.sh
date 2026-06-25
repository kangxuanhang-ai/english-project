#!/bin/sh
set -e

if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "Waiting for PostgreSQL..."
  until uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import async_session

async def check():
    async with async_session() as db:
        await db.execute(text('SELECT 1'))

asyncio.run(check())
" 2>/dev/null; do
    echo "  postgres not ready, retry in 3s..."
    sleep 3
  done
  echo "PostgreSQL is ready."

  echo "Ensuring langchain database..."
  uv run python docker/server/bootstrap.py

  echo "Running alembic migrations..."
  uv run alembic upgrade head

  echo "Seeding database (idempotent)..."
  uv run python seed.py || true
fi

exec "$@"

# NestJS → FastAPI 迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端从 NestJS (TypeScript) 全量迁移到 Python FastAPI，AI 服务从 LangChain JS 切换到 Python LangChain，前端完全不动。

**Architecture:** 两个独立 FastAPI 应用（app 端口 3000 + ai 端口 3001），共享 SQLAlchemy ORM 模型和客户端库。API 路径、端口、响应格式与 NestJS 版完全兼容。

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Alembic, python-jose, python-socketio, LangChain, langgraph-checkpoint-postgres, APScheduler

---

## 步骤 1: 项目骨架

**目标:** 重命名 server → serverOld，新建 server 文件夹，用 uv 初始化 Python 项目，创建完整目录结构。

**Files:**
- Rename: `server/` → `serverOld/`
- Create: `server/pyproject.toml`
- Create: `server/app/__init__.py`
- Create: `server/app/main.py`
- Create: `server/app/config.py`（空文件）
- Create: `server/app/database.py`（空文件）
- Create: `server/app/dependencies.py`（空文件）
- Create: `server/app/middleware.py`（空文件）
- Create: `server/app/models/__init__.py`
- Create: `server/app/schemas/__init__.py`
- Create: `server/app/routers/__init__.py`
- Create: `server/app/services/__init__.py`
- Create: `server/ai/__init__.py`
- Create: `server/ai/main.py`（空文件）
- Create: `server/ai/config.py`（空文件）
- Create: `server/ai/routers/__init__.py`
- Create: `server/ai/services/__init__.py`
- Create: `server/shared/__init__.py`
- Create: `server/shared/minio_client.py`（空文件）
- Create: `server/shared/alipay_client.py`（空文件）
- Create: `server/shared/email_client.py`（空文件）
- Create: `server/shared/clickhouse_client.py`（空文件）
- Modify: `pnpm-workspace.yaml`（移除 server 条目）

- [ ] **Step 1.1: 重命名 server → serverOld**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english"
mv server serverOld
```

验证：`ls serverOld/` 能看到原来的 NestJS 项目文件。

- [ ] **Step 1.2: 更新 pnpm-workspace.yaml**

移除 `server` 条目，因为新 server 是 Python 项目，不参与 pnpm 工作区。

```yaml
packages:
  - "packages/*"
  - "apps/*"
```

- [ ] **Step 1.3: 创建 pyproject.toml**

```toml
[project]
name = "english-server"
version = "0.1.0"
description = "English learning platform backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0",
    "alembic>=1.14",
    "asyncpg>=0.30",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "python-jose[cryptography]>=3.3",
    "minio>=7.2",
    "alipay-sdk-python>=4.0",
    "python-socketio[asyncio]>=5.11",
    "aiosmtplib>=3.0",
    "markdown2>=2.5",
    "langchain>=0.3",
    "langchain-deepseek>=0.1",
    "langgraph>=0.2",
    "langgraph-checkpoint-postgres>=2.0",
    "apscheduler>=3.10",
    "clickhouse-connect>=0.8",
    "nanoid>=2.0",
    "httpx>=0.28",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 1.4: 创建目录结构和空文件**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"

# 主 API 应用
mkdir -p app/models app/schemas app/routers app/services

# AI 服务
mkdir -p ai/routers ai/services

# 共享客户端
mkdir -p shared

# 创建 __init__.py 文件
touch app/__init__.py app/models/__init__.py app/schemas/__init__.py app/routers/__init__.py app/services/__init__.py
touch ai/__init__.py ai/routers/__init__.py ai/services/__init__.py
touch shared/__init__.py

# 创建主文件（内容后续步骤填充）
touch app/main.py app/config.py app/database.py app/dependencies.py app/middleware.py
touch ai/main.py ai/config.py
touch shared/minio_client.py shared/alipay_client.py shared/email_client.py shared/clickhouse_client.py
```

- [ ] **Step 1.5: 写 app/main.py 骨架**

```python
from fastapi import FastAPI

app = FastAPI(title="English Server", version="0.1.0")

@app.get("/")
async def root():
    return {"message": "access success"}
```

- [ ] **Step 1.6: 安装依赖并验证**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv sync
```

验证：
- `uv run python -c "import fastapi; print(fastapi.__version__)"` 输出版本号
- `uv run python -c "import app"` 不报错
- `uv run uvicorn app.main:app --port 3000` 启动成功
- 访问 `http://localhost:3000/` 返回 `{"message": "access success"}`

---

## 步骤 2: 配置模块

**目标:** 用 pydantic-settings 读取 .env 文件，提供全局配置对象。

**Files:**
- Create: `server/app/config.py`
- Create: `server/.env`（从 serverOld/.env 复制）

**参考:** 当前 NestJS 的 `ConfigModule.forRoot({ isGlobal: true, envFilePath: '.env' })` 和 `packages/config/index.ts`。

- [ ] **Step 2.1: 复制 .env 文件**

```bash
cp serverOld/.env server/.env
```

- [ ] **Step 2.2: 实现 config.py**

```python
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置，从 .env 文件读取"""

    # 数据库
    database_url: str = Field(alias="DATABASE_URL")

    # JWT
    secret_key: str = Field(alias="SECRET_KEY")

    # MinIO
    minio_endpoint: str = Field(alias="MINIO_ENDPOINT")
    minio_port: int = Field(default=9000, alias="MINIO_PORT")
    minio_use_ssl: bool = Field(default=False, alias="MINIO_USE_SSL")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="avatar", alias="MINIO_BUCKET")

    # DeepSeek
    deepseek_api_key: str = Field(alias="DEEPSEEK_API_KEY")
    deepseek_api_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_API_MODEL")
    deepseek_reasoner_api_model: str = Field(
        default="deepseek-reasoner", alias="DEEPSEEK_REASONER_API_MODEL"
    )

    # AI 数据库
    ai_database_url: str = Field(alias="AI_DATABASE_URL")

    # Bocha 搜索
    bocha_search_url: str = Field(alias="BOCHA_SEARCH_URL")
    bocha_api_key: str = Field(alias="BOCHA_API_KEY")

    # 支付宝
    alipay_app_id: str = Field(alias="ALIPAY_APP_ID")
    alipay_private_key: str = Field(alias="ALIPAY_PRIVATE_KEY")
    alipay_public_key: str = Field(alias="ALIPAY_PUBLIC_KEY")
    alipay_gateway: str = Field(alias="ALIPAY_GATEWAY")
    alipay_notify_url: str = Field(alias="ALIPAY_NOTIFY_URL")

    # 邮件
    email_host: str = Field(alias="EMAIL_HOST")
    email_port: int = Field(alias="EMAIL_PORT")
    email_use_ssl: bool = Field(default=False, alias="EMAIL_USE_SSL")
    email_user: str = Field(alias="EMAIL_USER")
    email_password: str = Field(alias="EMAIL_PASSWORD")
    email_from: str = Field(alias="EMAIL_FROM")

    # ClickHouse
    clickhouse_url: str = Field(default="", alias="CLICKHOUSE_URL")
    clickhouse_username: str = Field(default="", alias="CLICKHOUSE_USERNAME")
    clickhouse_password: str = Field(default="", alias="CLICKHOUSE_PASSWORD")
    clickhouse_database: str = Field(default="", alias="CLICKHOUSE_DATABASE")

    # 端口配置
    server_port: int = 3000
    ai_port: int = 3001
    web_port: int = 8080

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 2.3: 验证配置加载**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run python -c "from app.config import settings; print(f'DB: {settings.database_url}'); print(f'Port: {settings.server_port}')"
```

预期输出：
```
DB: postgresql://postgres:postgres@localhost:5432/english
Port: 3000
```

---

## 步骤 3: 数据库连接

**目标:** 配置 SQLAlchemy async engine 和 Session，替代 PrismaService。

**Files:**
- Create: `server/app/database.py`

**参考:** 当前 NestJS 的 `PrismaService` 使用 `PrismaPg` adapter 连接 PostgreSQL。

- [ ] **Step 3.1: 实现 database.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# async engine — 使用 asyncpg 驱动
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_size=10,
    max_overflow=20,
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
```

- [ ] **Step 3.2: 验证数据库连接**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import engine

async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT 1'))
        print(f'DB connection OK: {result.scalar()}')
    await engine.dispose()

asyncio.run(test())
"
```

预期输出：`DB connection OK: 1`

---

## 步骤 4: SQLAlchemy ORM 模型

**目标:** 将 Prisma schema 的 11 个模型全部转为 SQLAlchemy ORM 模型。

**Files:**
- Create: `server/app/models/__init__.py`（导出所有模型）
- Create: `server/app/models/user.py`
- Create: `server/app/models/word_book.py`
- Create: `server/app/models/course.py`
- Create: `server/app/models/payment.py`
- Create: `server/app/models/learn.py`
- Create: `server/app/models/visitor.py`

**参考:** `serverOld/prisma/schema.prisma` 中的完整模型定义。

- [ ] **Step 4.1: 实现 user.py**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    phone: Mapped[str] = mapped_column(String, unique=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    password: Mapped[str] = mapped_column(String)
    avatar: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    is_timing_task: Mapped[bool] = mapped_column(Boolean, default=False)
    timing_task_time: Mapped[str] = mapped_column(String, default="00:00:00")
    word_number: Mapped[int] = mapped_column(Integer, default=0)
    day_number: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关系
    word_book_records = relationship("WordBookRecord", back_populates="user", cascade="all, delete-orphan")
    payment_records = relationship("PaymentRecord", back_populates="user", cascade="all, delete-orphan")
    course_records = relationship("CourseRecord", back_populates="user", cascade="all, delete-orphan")
    visitors = relationship("Visitor", back_populates="user", cascade="all, delete-orphan")
```

- [ ] **Step 4.2: 实现 word_book.py**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WordBook(Base):
    __tablename__ = "word_book"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    word: Mapped[str] = mapped_column(String)
    phonetic: Mapped[str | None] = mapped_column(String, nullable=True)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    pos: Mapped[str | None] = mapped_column(String, nullable=True)
    collins: Mapped[str | None] = mapped_column(String, nullable=True)
    oxford: Mapped[str | None] = mapped_column(String, nullable=True)
    tag: Mapped[str | None] = mapped_column(String, nullable=True)
    bnc: Mapped[str | None] = mapped_column(String, nullable=True)
    frq: Mapped[str | None] = mapped_column(String, nullable=True)
    exchange: Mapped[str | None] = mapped_column(Text, nullable=True)
    gk: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    zk: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    gre: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    toefl: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ielts: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cet6: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cet4: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ky: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    word_book_records = relationship("WordBookRecord", back_populates="word")

    __table_args__ = (
        Index("idx_word_book_word", "word"),
        Index("idx_word_book_tag", "tag"),
        Index("idx_word_book_word_tag", "word", "tag"),
    )


class WordBookRecord(Base):
    __tablename__ = "word_book_record"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    word_id: Mapped[str] = mapped_column(String(30), ForeignKey("word_book.id", ondelete="CASCADE"), nullable=False)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    user_id: Mapped[str] = mapped_column(String(30), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="word_book_records")
    word = relationship("WordBook", back_populates="word_book_records")

    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_word_book_record_user_word"),
    )
```

- [ ] **Step 4.3: 实现 course.py**

```python
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Course(Base):
    __tablename__ = "course"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    course_records = relationship("CourseRecord", back_populates="course")


class CourseRecord(Base):
    __tablename__ = "course_record"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(30), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[str] = mapped_column(String(30), ForeignKey("course.id", ondelete="CASCADE"), nullable=False)
    is_purchased: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    payment_record_id: Mapped[str | None] = mapped_column(
        String(30), ForeignKey("payment_record.id", ondelete="CASCADE"), nullable=True
    )

    user = relationship("User", back_populates="course_records")
    course = relationship("Course", back_populates="course_records")
    payment_record = relationship("PaymentRecord", back_populates="course_records")

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_course_record_user_course"),
    )
```

- [ ] **Step 4.4: 实现 payment.py**

```python
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

import enum


class TradeStatus(str, enum.Enum):
    NOT_PAY = "NOT_PAY"
    WAIT_BUYER_PAY = "WAIT_BUYER_PAY"
    TRADE_CLOSED = "TRADE_CLOSED"
    TRADE_SUCCESS = "TRADE_SUCCESS"
    TRADE_FINISHED = "TRADE_FINISHED"


class PaymentRecord(Base):
    __tablename__ = "payment_record"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(30), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    trade_no: Mapped[str | None] = mapped_column(String, nullable=True)
    out_trade_no: Mapped[str] = mapped_column(String, unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    trade_status: Mapped[TradeStatus] = mapped_column(
        Enum(TradeStatus), default=TradeStatus.NOT_PAY
    )
    send_pay_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="payment_records")
    course_records = relationship("CourseRecord", back_populates="payment_record")
```

- [ ] **Step 4.5: 实现 visitor.py（含 PageView、TrackEvent、PerformanceEntry、ErrorEntry）**

```python
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Visitor(Base):
    __tablename__ = "visitor"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    anonymous_id: Mapped[str] = mapped_column(String, unique=True)
    user_id: Mapped[str | None] = mapped_column(
        String(30), ForeignKey("user.id", ondelete="CASCADE"), nullable=True
    )
    browser: Mapped[str | None] = mapped_column(String, nullable=True)
    os: Mapped[str | None] = mapped_column(String, nullable=True)
    device: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="visitors")
    page_views = relationship("PageView", back_populates="visitor", cascade="all, delete-orphan")
    track_events = relationship("TrackEvent", back_populates="visitor", cascade="all, delete-orphan")
    performance_entries = relationship("PerformanceEntry", back_populates="visitor", cascade="all, delete-orphan")
    error_entries = relationship("ErrorEntry", back_populates="visitor", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_visitor_user_id", "user_id"),
        Index("idx_visitor_anonymous_id", "anonymous_id"),
    )


class PageView(Base):
    __tablename__ = "page_view"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("visitor.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String)
    referrer: Mapped[str | None] = mapped_column(String, nullable=True)
    path: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    visitor = relationship("Visitor", back_populates="page_views")

    __table_args__ = (
        Index("idx_page_view_visitor_created", "visitor_id", "created_at"),
        Index("idx_page_view_path_created", "path", "created_at"),
    )


class TrackEvent(Base):
    __tablename__ = "track_event"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("visitor.id", ondelete="CASCADE"), nullable=False
    )
    event: Mapped[str] = mapped_column(String)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    visitor = relationship("Visitor", back_populates="track_events")

    __table_args__ = (
        Index("idx_track_event_visitor_created", "visitor_id", "created_at"),
        Index("idx_track_event_event_created", "event", "created_at"),
    )


class PerformanceEntry(Base):
    __tablename__ = "performance_entry"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("visitor.id", ondelete="CASCADE"), nullable=False
    )
    fp: Mapped[float | None] = mapped_column(Float, nullable=True)
    fcp: Mapped[float | None] = mapped_column(Float, nullable=True)
    lcp: Mapped[float | None] = mapped_column(Float, nullable=True)
    inp: Mapped[float | None] = mapped_column(Float, nullable=True)
    cls: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    visitor = relationship("Visitor", back_populates="performance_entries")

    __table_args__ = (
        Index("idx_performance_entry_fp_created", "fp", "created_at"),
        Index("idx_performance_entry_fcp_created", "fcp", "created_at"),
        Index("idx_performance_entry_lcp_created", "lcp", "created_at"),
        Index("idx_performance_entry_inp_created", "inp", "created_at"),
        Index("idx_performance_entry_cls_created", "cls", "created_at"),
        Index("idx_performance_entry_all_metrics", "fp", "fcp", "lcp", "inp", "cls", "created_at"),
    )


class ErrorEntry(Base):
    __tablename__ = "error_entry"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    visitor_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("visitor.id", ondelete="CASCADE"), nullable=False
    )
    error: Mapped[str] = mapped_column(String)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    visitor = relationship("Visitor", back_populates="error_entries")

    __table_args__ = (
        Index("idx_error_entry_visitor_created", "visitor_id", "created_at"),
        Index("idx_error_entry_error_created", "error", "created_at"),
    )
```

- [ ] **Step 4.6: 实现 models/__init__.py 导出所有模型**

```python
from app.models.user import User
from app.models.word_book import WordBook, WordBookRecord
from app.models.course import Course, CourseRecord
from app.models.payment import PaymentRecord, TradeStatus
from app.models.visitor import (
    Visitor,
    PageView,
    TrackEvent,
    PerformanceEntry,
    ErrorEntry,
)

__all__ = [
    "User",
    "WordBook",
    "WordBookRecord",
    "Course",
    "CourseRecord",
    "PaymentRecord",
    "TradeStatus",
    "Visitor",
    "PageView",
    "TrackEvent",
    "PerformanceEntry",
    "ErrorEntry",
]
```

- [ ] **Step 4.7: 验证模型导入**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run python -c "
from app.models import User, WordBook, WordBookRecord, Course, CourseRecord, PaymentRecord, TradeStatus, Visitor, PageView, TrackEvent, PerformanceEntry, ErrorEntry
print(f'Models loaded: {len([User, WordBook, WordBookRecord, Course, CourseRecord, PaymentRecord, Visitor, PageView, TrackEvent, PerformanceEntry, ErrorEntry])}')
print(f'TradeStatus values: {[s.value for s in TradeStatus]}')
"
```

预期输出：
```
Models loaded: 11
TradeStatus values: ['NOT_PAY', 'WAIT_BUYER_PAY', 'TRADE_CLOSED', 'TRADE_SUCCESS', 'TRADE_FINISHED']
```

---

## 步骤 5: Alembic 迁移

**目标:** 初始化 Alembic，生成初始迁移脚本，验证与现有数据库 schema 兼容。

**Files:**
- Create: `server/alembic.ini`
- Create: `server/alembic/env.py`
- Create: `server/alembic/script.py.mako`
- Create: `server/alembic/versions/`（目录）

- [ ] **Step 5.1: 初始化 Alembic**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run alembic init alembic
```

- [ ] **Step 5.2: 配置 alembic.ini**

编辑 `alembic.ini`，找到 `sqlalchemy.url` 行并注释掉（我们从 env.py 动态设置）：

```ini
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

- [ ] **Step 5.3: 配置 alembic/env.py**

替换 `alembic/env.py` 的全部内容：

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.config import settings
from app.database import Base

# 导入所有模型，确保 Base.metadata 包含所有表
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    connectable = async_engine_from_config(
        {"sqlalchemy.url": url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5.4: 生成初始迁移**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run alembic revision --autogenerate -m "initial tables"
```

- [ ] **Step 5.5: 检查生成的迁移脚本**

打开 `alembic/versions/` 下最新生成的 `.py` 文件，确认：
- 包含所有 11 个表的 `op.create_table()`
- 有正确的外键约束和 `ondelete='CASCADE'`
- 有所有索引定义
- 有 `UniqueConstraint`（word_book_record 的 user_id+word_id，course_record 的 user_id+course_id）

如果生成的迁移有差异（比如缺少索引），手动修正迁移脚本。

- [ ] **Step 5.6: 执行迁移（在测试库上）**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run alembic upgrade head
```

验证：
- 连接数据库检查表是否创建成功
- `uv run alembic current` 显示最新版本
- `uv run alembic history` 显示迁移历史

- [ ] **Step 5.7: 验证与现有 schema 一致**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import engine
from app.models import Base

async def check():
    async with engine.connect() as conn:
        for table_name in Base.metadata.tables:
            result = await conn.execute(
                text(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = :name)\"),
                {\"name\": table_name}
            )
            exists = result.scalar()
            print(f'{table_name}: {\"OK\" if exists else \"MISSING\"}')
    await engine.dispose()

asyncio.run(check())
"
```

预期：所有 11 个表都显示 `OK`。

---

## 步骤 6: 全局中间件

**目标:** 实现响应信封（统一返回格式）和异常过滤器，与 NestJS 版完全兼容。

**Files:**
- Create: `server/app/middleware.py`

**参考:** `serverOld/libs/shared/src/interceptor/interceptor.ts` 和 `exceptionFilter.ts`。

- [ ] **Step 6.1: 实现 middleware.py**

```python
import json
from datetime import datetime

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def transform_bigint(obj):
    """将 bigint 转换为字符串，保留 Date 类型不变（Python 无 bigint 问题，但保持接口一致）"""
    if isinstance(obj, list):
        return [transform_bigint(item) for item in obj]
    if isinstance(obj, dict):
        return {key: transform_bigint(value) for key, value in obj.items()}
    return obj


async def response_envelope_middleware(request: Request, call_next):
    """全局响应信封中间件：包装所有成功响应为统一格式"""
    # 跳过 Socket.IO 路径（WebSocket 握手不能被拦截）
    if request.url.path.startswith("/socket.io"):
        return await call_next(request)

    response = await call_next(request)

    # 只处理 JSON 响应（2xx 状态码）
    if response.status_code >= 200 and response.status_code < 300:
        # 读取原始响应体
        body = b""
        async for chunk in response.body_iterator:
            body += chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")

        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return response

        # 如果已经是信封格式（有 code 和 data 字段），直接包装
        if isinstance(data, dict) and "code" in data and "data" in data:
            envelope = {
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "message": data.get("message", "请求成功"),
                "code": data.get("code", 200),
                "success": True,
                "data": transform_bigint(data.get("data")),
            }
        else:
            # 普通响应，直接包装
            envelope = {
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "message": "请求成功",
                "code": 200,
                "success": True,
                "data": transform_bigint(data),
            }

        return JSONResponse(content=envelope, status_code=response.status_code)

    return response


async def exception_handler(request: Request, exc):
    """全局异常处理器：统一错误响应格式"""
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "message": str(exc.detail),
                "code": exc.status_code,
                "success": False,
            },
        )

    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "timestamp": datetime.now().isoformat(),
                "path": request.url.path,
                "message": "请求参数验证失败",
                "code": 422,
                "success": False,
            },
        )

    # 未知异常
    return JSONResponse(
        status_code=500,
        content={
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
            "message": str(exc),
            "code": 500,
            "success": False,
        },
    )
```

- [ ] **Step 6.2: 更新 app/main.py 注册中间件**

```python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.middleware import response_envelope_middleware, exception_handler

app = FastAPI(title="English Server", version="0.1.0")

# 注册全局中间件
app.middleware("http")(response_envelope_middleware)

# 注册全局异常处理器
app.add_exception_handler(StarletteHTTPException, exception_handler)
app.add_exception_handler(RequestValidationError, exception_handler)


@app.get("/")
async def root():
    return {"message": "access success"}
```

- [ ] **Step 6.3: 验证响应信封**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run uvicorn app.main:app --port 3000 &
sleep 2
curl http://localhost:3000/
```

预期输出：
```json
{
  "timestamp": "...",
  "path": "/",
  "message": "请求成功",
  "code": 200,
  "success": true,
  "data": {"message": "access success"}
}
```

- [ ] **Step 6.4: 验证异常处理**

```bash
curl http://localhost:3000/nonexistent
```

预期输出（404）：
```json
{
  "timestamp": "...",
  "path": "/nonexistent",
  "message": "Not Found",
  "code": 404,
  "success": false
}
```

---

## 步骤 7: MinIO 客户端

**目标:** 实现 MinIO 客户端初始化，包括 bucket 创建和公共读策略。

**Files:**
- Create: `server/shared/minio_client.py`

**参考:** `serverOld/libs/shared/src/minio/minio.service.ts`。

- [ ] **Step 7.1: 实现 minio_client.py**

```python
import json

from minio import Minio
from minio.error import S3Error

from app.config import settings


class MinioClient:
    """MinIO 客户端封装"""

    def __init__(self):
        self.client = Minio(
            endpoint=f"{settings.minio_endpoint}:{settings.minio_port}",
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
        self.bucket = settings.minio_bucket

    async def init_bucket(self):
        """初始化 bucket：不存在则创建并设置公共读策略"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                # 设置公共读策略（与 NestJS 版一致）
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadObjects",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket}/*"],
                        }
                    ],
                }
                self.client.set_bucket_policy(self.bucket, json.dumps(policy))
                print(f"MinIO bucket '{self.bucket}' created with public read policy")
            else:
                print(f"MinIO bucket '{self.bucket}' already exists")
        except S3Error as e:
            print(f"MinIO init error: {e}")

    def get_client(self) -> Minio:
        return self.client

    def get_bucket(self) -> str:
        return self.bucket


# 全局单例
minio_client = MinioClient()
```

- [ ] **Step 7.2: 验证 MinIO 连接**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run python -c "
import asyncio
from shared.minio_client import minio_client

async def test():
    await minio_client.init_bucket()
    print(f'Bucket: {minio_client.get_bucket()}')
    print(f'Client: {minio_client.get_client()}')

asyncio.run(test())
"
```

预期输出：`MinIO bucket 'avatar' already exists`（或创建成功）。

---

## 步骤 8: JWT 认证

**目标:** 实现 JWT token 生成（双 token 机制）和验证依赖（AuthGuard 替代）。

**Files:**
- Create: `server/app/services/auth.py`
- Create: `server/app/dependencies.py`

**参考:** `serverOld/apps/server/src/auth/auth.service.ts` 和 `serverOld/libs/shared/src/auth/auth.guard.ts`。

- [ ] **Step 8.1: 实现 services/auth.py**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"


def create_access_token(payload: dict) -> str:
    """生成 access token（10秒过期，与 NestJS 版一致）"""
    to_encode = {**payload, "tokenType": "access"}
    expire = datetime.now(timezone.utc) + timedelta(seconds=10)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(payload: dict) -> str:
    """生成 refresh token（7 天过期）"""
    to_encode = {**payload, "tokenType": "refresh"}
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def generate_tokens(payload: dict) -> dict:
    """生成 access + refresh token 对（对应 NestJS AuthService.generateToken）"""
    return {
        "accessToken": create_access_token(payload),
        "refreshToken": create_refresh_token(payload),
    }


def verify_token(token: str, expected_type: str = "access") -> dict:
    """验证 JWT token，返回 payload。tokenType 不匹配时抛异常。"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("tokenType") != expected_type:
            raise ValueError(f"Invalid token type: expected {expected_type}")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")
```

- [ ] **Step 8.2: 实现 dependencies.py（AuthGuard 替代）**

```python
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth import verify_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI 依赖注入：验证 access token 并返回用户 payload。
    对应 NestJS 的 AuthGuard。
    """
    token = credentials.credentials
    try:
        payload = verify_token(token, expected_type="access")
        return payload
    except ValueError:
        raise HTTPException(status_code=401, detail="token已过期或无效")


async def get_current_user_optional(
    request: Request,
) -> dict | None:
    """可选认证：有 token 则验证，没有则返回 None"""
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    try:
        token = auth.split(" ")[1]
        return verify_token(token, expected_type="access")
    except (ValueError, IndexError):
        return None
```

- [ ] **Step 8.3: 验证 JWT 生成和验证**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run python -c "
from app.services.auth import generate_tokens, verify_token

# 生成 token
tokens = generate_tokens({'userId': 'test123', 'name': 'test', 'email': 'test@test.com'})
print(f'Access token: {tokens[\"accessToken\"][:50]}...')
print(f'Refresh token: {tokens[\"refreshToken\"][:50]}...')

# 验证 access token
payload = verify_token(tokens['accessToken'], expected_type='access')
print(f'Payload: {payload}')

# 验证 refresh token
payload = verify_token(tokens['refreshToken'], expected_type='refresh')
print(f'Refresh payload: {payload}')

# 错误类型验证
try:
    verify_token(tokens['accessToken'], expected_type='refresh')
except ValueError as e:
    print(f'Expected error: {e}')
"
```

预期输出：
```
Access token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Refresh token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Payload: {'userId': 'test123', 'name': 'test', 'email': 'test@test.com', 'tokenType': 'access'}
Refresh payload: {'userId': 'test123', 'name': 'test', 'email': 'test@test.com', 'tokenType': 'refresh', 'exp': ...}
Expected error: Invalid token type: expected refresh
```

---

## 步骤 9: Alipay 客户端

**目标:** 初始化支付宝 SDK 客户端。

**Files:**
- Create: `server/shared/alipay_client.py`

**参考:** `serverOld/libs/shared/src/pay/pay.service.ts`。

- [ ] **Step 9.1: 实现 alipay_client.py**

```python
from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient

from app.config import settings


class AlipayClient:
    """支付宝客户端封装（alipay-sdk-python v4）"""

    def __init__(self):
        config = AlipayClientConfig()
        config.server_url = settings.alipay_gateway
        config.app_id = settings.alipay_app_id
        config.app_private_key = settings.alipay_private_key
        config.alipay_public_key = settings.alipay_public_key
        # charset 默认 utf-8，sign_type 默认 RSA2
        self.client = DefaultAlipayClient(alipay_sdk=config)

    def get_client(self) -> DefaultAlipayClient:
        return self.client


# 全局单例
alipay_client = AlipayClient()
```

- [ ] **Step 9.2: 验证支付宝客户端初始化**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run python -c "
from shared.alipay_client import alipay_client
print(f'Alipay client: {alipay_client.get_client()}')
"
```

预期：无报错，输出客户端对象地址。

---

## 步骤 10: User 模块 — 注册 + 登录

**目标:** 实现用户注册和登录接口，与 NestJS 版 API 完全兼容。

**Files:**
- Create: `server/app/schemas/user.py`
- Create: `server/app/services/user.py`
- Create: `server/app/routers/user.py`
- Modify: `server/app/main.py`（注册路由）

**参考:**
- `serverOld/apps/server/src/user/user.controller.ts` — 路由定义
- `serverOld/apps/server/src/user/user.service.ts` — 业务逻辑
- `serverOld/apps/server/src/user/user.select.ts` — Prisma select

- [ ] **Step 10.1: 实现 schemas/user.py**

```python
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
```

- [ ] **Step 10.2: 实现 services/user.py**

```python
from datetime import datetime, timezone

from nanoid import generate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth import generate_tokens, verify_token


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

    # 创建用户
    user = User(
        id=generate(size=20),
        name=data["name"],
        phone=data["phone"],
        email=data.get("email"),
        password=data["password"],  # 前端已 MD5 哈希，直接存储
    )
    db.add(user)
    await db.flush()  # 获取 ID
    await db.commit()  # 显式提交（get_db 不自动 commit）

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

    # 验证密码（前端 MD5 哈希后的值直接比较）
    if user.password != data["password"]:
        raise ValueError("密码错误")

    # 更新最后登录时间
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()

    # 生成 token
    token = generate_tokens({"userId": user.id, "name": user.name, "email": user.email})

    return user_to_response(user, token)
```

- [ ] **Step 10.3: 实现 routers/user.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserLogin, UserRegister
from app.services.user import login_user, register_user

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
```

- [ ] **Step 10.4: 注册路由到 main.py**

```python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.middleware import response_envelope_middleware, exception_handler
from app.routers import user

app = FastAPI(title="English Server", version="0.1.0")

# 注册全局中间件
app.middleware("http")(response_envelope_middleware)

# 注册全局异常处理器
app.add_exception_handler(StarletteHTTPException, exception_handler)
app.add_exception_handler(RequestValidationError, exception_handler)

# 注册路由
app.include_router(user.router)


@app.get("/")
async def root():
    return {"message": "access success"}
```

- [ ] **Step 10.5: 验证注册接口**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run uvicorn app.main:app --port 3000 &
sleep 2

# 注册
curl -X POST http://localhost:3000/api/v1/user/register \
  -H "Content-Type: application/json" \
  -d '{"name":"test","phone":"13800138000","password":"e10adc3949ba59abbe56e057f20f883e"}'
```

预期输出：
```json
{
  "timestamp": "...",
  "path": "/api/v1/user/register",
  "message": "注册成功",
  "code": 200,
  "success": true,
  "data": {
    "id": "...",
    "name": "test",
    "phone": "13800138000",
    "token": {"accessToken": "...", "refreshToken": "..."},
    ...
  }
}
```

- [ ] **Step 10.6: 验证登录接口**

```bash
curl -X POST http://localhost:3000/api/v1/user/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","password":"e10adc3949ba59abbe56e057f20f883e"}'
```

预期输出：与注册响应格式一致，包含 token。

---

## 步骤 11: User — refresh-token + upload-avatar + update-user

**目标:** 完成用户模块剩余 3 个接口。

**Files:**
- Modify: `server/app/services/user.py`
- Modify: `server/app/routers/user.py`

**参考:** `serverOld/apps/server/src/user/user.service.ts` 中的 `refreshToken`、`uploadAvatar`、`updateUser` 方法。

- [ ] **Step 11.1: 在 services/user.py 中添加 refresh_user_token**

```python
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
    token = generate_tokens({"userId": user.id, "name": user.name, "email": user.email})
    return token
```

- [ ] **Step 11.2: 在 services/user.py 中添加 upload_avatar**

```python
import time
from io import BytesIO

from shared.minio_client import minio_client
from app.config import settings


async def upload_avatar(file) -> dict:
    """
    上传头像到 MinIO。
    对应 NestJS UserService.uploadAvatar。
    """
    if not file:
        raise ValueError("文件不存在")

    content = await file.read()
    if len(content) > 1024 * 1024 * 5:
        raise ValueError("文件大小不能超过5MB")

    client = minio_client.get_client()
    bucket = minio_client.get_bucket()

    # 生成文件名
    file_name = f"{int(time.time() * 1000)}-{file.filename}"

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
    database_url = f"/{bucket}/{file_name}"
    preview_url = f"{protocol}://{settings.minio_endpoint}:{settings.minio_port}{database_url}"

    return {"previewUrl": preview_url, "databaseUrl": database_url}
```

- [ ] **Step 11.3: 在 services/user.py 中添加 update_user**

```python
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
    }
```

- [ ] **Step 11.4: 在 routers/user.py 中添加路由**

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import UserLogin, UserRegister, UserUpdate
from app.services.user import login_user, register_user, refresh_user_token, upload_avatar, update_user

router = APIRouter(prefix="/api/v1/user", tags=["user"])


@router.post("/register")
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    try:
        result = await register_user(db, data.model_dump())
        return {"data": result, "code": 200, "message": "注册成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
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
async def upload(file: UploadFile = File(...)):
    """上传头像。对应 NestJS POST /api/v1/user/upload-avatar"""
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
```

- [ ] **Step 11.5: 验证所有接口**

```bash
# 刷新 token
curl -X POST http://localhost:3000/api/v1/user/refresh-token \
  -H "Content-Type: application/json" \
  -d '{"refreshToken":"<从登录响应获取>"}'

# 上传头像
curl -X POST http://localhost:3000/api/v1/user/upload-avatar \
  -F "file=@/path/to/avatar.jpg"

# 更新用户（需要 token）
curl -X POST http://localhost:3000/api/v1/user/update-user \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <accessToken>" \
  -d '{"name":"new name","bio":"hello"}'
```

---

## 步骤 12: WordBook — 分页查询 + 标签过滤

**目标:** 实现单词本查询接口。

**Files:**
- Create: `server/app/schemas/word_book.py`
- Create: `server/app/services/word_book.py`
- Create: `server/app/routers/word_book.py`
- Modify: `server/app/main.py`

**参考:** `serverOld/apps/server/src/word-book/word-book.service.ts`。

- [ ] **Step 12.1: 实现 schemas/word_book.py**

```python
from pydantic import BaseModel


class WordQuery(BaseModel):
    page: int = 1
    pageSize: int = 12
    word: str | None = None
    gk: str | None = None
    zk: str | None = None
    gre: str | None = None
    toefl: str | None = None
    ielts: str | None = None
    cet6: str | None = None
    cet4: str | None = None
    ky: str | None = None
```

- [ ] **Step 12.2: 实现 services/word_book.py**

```python
from sqlalchemy import cast, func, Integer, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.word_book import WordBook


def to_boolean(value: str | None) -> bool | None:
    """将字符串 'true' 转为布尔值，对应 NestJS 的 toBoolean"""
    if value == "true":
        return True
    return None


async def get_word_book_list(db: AsyncSession, query: dict) -> dict:
    """
    分页查询单词列表，支持标签过滤。
    对应 NestJS WordBookService.findAll。
    """
    page = query.get("page", 1)
    page_size = query.get("pageSize", 12)
    word = query.get("word")

    # 构建过滤条件
    filters = []
    if word:
        filters.append(WordBook.word.contains(word))

    # 标签过滤
    for tag in ["gk", "zk", "gre", "toefl", "ielts", "cet6", "cet4", "ky"]:
        val = to_boolean(query.get(tag))
        if val is not None:
            filters.append(getattr(WordBook, tag) == val)

    where_clause = filters if filters else []

    # 查询总数
    count_stmt = select(func.count()).select_from(WordBook)
    for f in where_clause:
        count_stmt = count_stmt.where(f)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 查询列表
    list_stmt = select(WordBook)
    for f in where_clause:
        list_stmt = list_stmt.where(f)
    list_stmt = list_stmt.order_by(cast(WordBook.frq, Integer).desc())
    list_stmt = list_stmt.offset((page - 1) * page_size).limit(page_size)

    list_result = await db.execute(list_stmt)
    words = list_result.scalars().all()

    # 转为响应格式
    word_list = []
    for w in words:
        word_list.append({
            "id": w.id,
            "word": w.word,
            "phonetic": w.phonetic,
            "definition": w.definition,
            "translation": w.translation,
            "pos": w.pos,
            "collins": w.collins,
            "oxford": w.oxford,
            "tag": w.tag,
            "bnc": w.bnc,
            "frq": w.frq,
            "exchange": w.exchange,
            "gk": w.gk,
            "zk": w.zk,
            "gre": w.gre,
            "toefl": w.toefl,
            "ielts": w.ielts,
            "cet6": w.cet6,
            "cet4": w.cet4,
            "ky": w.ky,
        })

    return {"total": total, "list": word_list}
```

- [ ] **Step 12.3: 实现 routers/word_book.py**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.word_book import get_word_book_list

router = APIRouter(prefix="/api/v1/word-book", tags=["word-book"])


@router.get("")
async def list_words(
    page: int = Query(1),
    pageSize: int = Query(12),
    word: str | None = Query(None),
    gk: str | None = Query(None),
    zk: str | None = Query(None),
    gre: str | None = Query(None),
    toefl: str | None = Query(None),
    ielts: str | None = Query(None),
    cet6: str | None = Query(None),
    cet4: str | None = Query(None),
    ky: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """分页查询单词。对应 NestJS GET /api/v1/word-book"""
    query = {
        "page": page, "pageSize": pageSize, "word": word,
        "gk": gk, "zk": zk, "gre": gre, "toefl": toefl,
        "ielts": ielts, "cet6": cet6, "cet4": cet4, "ky": ky,
    }
    result = await get_word_book_list(db, query)
    return {"data": result, "code": 200, "message": "查询成功"}
```

- [ ] **Step 12.4: 注册路由到 main.py**

```python
from app.routers import user, word_book
# ...
app.include_router(user.router)
app.include_router(word_book.router)
```

- [ ] **Step 12.5: 验证接口**

```bash
curl "http://localhost:3000/api/v1/word-book?page=1&pageSize=5&gk=true"
```

预期：返回 `{"data": {"total": ..., "list": [...]}, "code": 200, ...}`。

---

## 步骤 13: Course — 课程列表 + 我的课程

**目标:** 实现课程查询接口。

**Files:**
- Create: `server/app/schemas/course.py`
- Create: `server/app/services/course.py`
- Create: `server/app/routers/course.py`
- Modify: `server/app/main.py`

**参考:** `serverOld/apps/server/src/course/course.service.ts`。

- [ ] **Step 13.1: 实现 services/course.py**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, CourseRecord
from app.models.payment import PaymentRecord, TradeStatus


async def get_course_list(db: AsyncSession) -> list:
    """获取所有课程。对应 NestJS CourseService.findAll"""
    result = await db.execute(select(Course))
    courses = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "value": c.value,
            "description": c.description,
            "teacher": c.teacher,
            "url": c.url,
            "price": f"{c.price:.2f}",
        }
        for c in courses
    ]


async def get_my_courses(db: AsyncSession, user_id: str) -> list:
    """获取用户已购课程。对应 NestJS CourseService.findMy"""
    result = await db.execute(
        select(CourseRecord)
        .join(CourseRecord.payment_record)
        .where(
            CourseRecord.user_id == user_id,
            PaymentRecord.trade_status == TradeStatus.TRADE_SUCCESS,
        )
        .join(CourseRecord.course)
    )
    records = result.scalars().all()

    courses = []
    for record in records:
        course = record.course
        courses.append({
            "id": course.id,
            "name": course.name,
            "value": course.value,
            "description": course.description,
            "teacher": course.teacher,
            "url": course.url,
            "price": f"{course.price:.2f}",
        })
    return courses
```

- [ ] **Step 13.2: 实现 routers/course.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.course import get_course_list, get_my_courses

router = APIRouter(prefix="/api/v1/course", tags=["course"])


@router.get("/list")
async def list_courses(db: AsyncSession = Depends(get_db)):
    """课程列表。对应 NestJS GET /api/v1/course/list"""
    result = await get_course_list(db)
    return {"data": result, "code": 200, "message": "查询成功"}


@router.get("/my")
async def my_courses(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """我的课程。对应 NestJS GET /api/v1/course/my（需要认证）"""
    result = await get_my_courses(db, user["userId"])
    return {"data": result, "code": 200, "message": "查询成功"}
```

- [ ] **Step 13.3: 注册路由并验证**

```python
from app.routers import user, word_book, course
app.include_router(course.router)
```

```bash
curl http://localhost:3000/api/v1/course/list
```

---

## 步骤 14: Email 客户端 + Socket.IO

**目标:** 实现邮件发送和 Socket.IO 实时通知。

**Files:**
- Create: `server/shared/email_client.py`
- Create: `server/app/services/socket.py`
- Modify: `server/app/main.py`

**参考:**
- `serverOld/libs/shared/src/email/email.service.ts`
- `serverOld/apps/server/src/socket/socket.gateway.ts`

- [ ] **Step 14.1: 实现 shared/email_client.py**

```python
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


async def send_email(to: str, subject: str, html: str) -> bool:
    """
    发送 HTML 邮件。
    对应 NestJS EmailService.sendEmail。
    """
    try:
        message = MIMEMultipart("alternative")
        message["From"] = settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message.attach(MIMEText(html, "html"))

        await aiosmtplib.send(
            message,
            hostname=settings.email_host,
            port=settings.email_port,
            use_tls=settings.email_use_ssl,
            username=settings.email_user,
            password=settings.email_password,
        )
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False
```

- [ ] **Step 14.2: 实现 services/socket.py**

```python
import socketio

# 创建 Socket.IO 服务（asyncio 模式，兼容客户端 v4/v5）
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


@sio.event
async def connect(sid, environ):
    """客户端连接时加入用户房间"""
    from urllib.parse import parse_qs

    query = parse_qs(environ.get("QUERY_STRING", ""))
    user_id = query.get("userId", [None])[0]
    if user_id:
        await sio.enter_room(sid, f"user_{user_id}")
        print(f"Socket.IO: user_{user_id} connected")


@sio.event
async def disconnect(sid):
    """客户端断开连接"""
    pass


async def emit_payment_success(user_id: str):
    """
    向指定用户发送支付成功通知。
    对应 NestJS SocketGateway.emitPaymentSuccess。
    """
    await sio.emit("paymentSuccess", user_id, room=f"user_{user_id}")
```

- [ ] **Step 14.3: 在 main.py 中挂载 Socket.IO**

```python
import socketio
from app.services.socket import sio

# 创建 FastAPI app
app = FastAPI(title="English Server", version="0.1.0")

# ... 中间件和路由注册 ...

# 挂载 Socket.IO（必须在路由之后）
socket_app = socketio.ASGIApp(sio, app)
```

> **注意:** uvicorn 启动时要用 `socket_app` 而不是 `app`：
> `uvicorn app.main:socket_app --port 3000`

- [ ] **Step 14.4: 验证 Socket.IO 连接**

用浏览器打开控制台：
```javascript
const socket = io("http://localhost:3000", { query: { userId: "test123" } });
socket.on("connect", () => console.log("connected"));
socket.on("paymentSuccess", (data) => console.log("payment:", data));
```

---

## 步骤 15: Pay — 创建订单 + 回调 + Socket.IO 通知

**目标:** 实现支付宝支付全流程。

**Files:**
- Create: `server/app/schemas/pay.py`
- Create: `server/app/services/pay.py`
- Create: `server/app/routers/pay.py`
- Modify: `server/app/main.py`

**参考:** `serverOld/apps/server/src/pay/pay.service.ts`。

- [ ] **Step 15.1: 实现 schemas/pay.py**

```python
from pydantic import BaseModel


class CreatePayDto(BaseModel):
    subject: str
    body: str
    total_amount: float
    courseId: str
```

- [ ] **Step 15.2: 实现 services/pay.py**

```python
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from nanoid import generate

from app.models.payment import PaymentRecord, TradeStatus
from app.models.course import CourseRecord
from app.services.socket import emit_payment_success
from app.config import settings
from shared.alipay_client import alipay_client


def create_trade_no() -> str:
    """生成订单号，格式 XM-<nanoid>"""
    return f"XM-{generate(size=12)}"


async def create_payment(db: AsyncSession, data: dict, user_id: str) -> dict:
    """
    创建支付订单。
    对应 NestJS PayService.create。
    """
    # 检查是否已购买
    existing = await db.execute(
        select(CourseRecord).where(
            CourseRecord.user_id == user_id,
            CourseRecord.course_id == data["courseId"],
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("您已经购买过该课程")

    # 创建支付记录
    out_trade_no = create_trade_no()
    payment = PaymentRecord(
        user_id=user_id,
        out_trade_no=out_trade_no,
        amount=data["total_amount"],
        subject=data["subject"],
        body=data["body"],
    )
    db.add(payment)
    await db.flush()
    await db.commit()

    # 生成支付宝支付 URL
    time_expire = datetime.now(timezone.utc) + timedelta(minutes=1)

    # 注意：alipay-sdk-python 的 API 与 JS 版略有不同
    # 这里使用 pageExecute 方法
    biz_content = {
        "out_trade_no": out_trade_no,
        "total_amount": str(data["total_amount"]),
        "subject": data["subject"],
        "body": json.dumps({"courseId": data["courseId"], "userId": user_id}),
        "product_code": "FAST_INSTANT_TRADE_PAY",
        "time_expire": time_expire.strftime("%Y-%m-%d %H:%M:%S"),
    }

    pay_url = alipay_client.get_client().page_execute(
        "alipay.trade.page.pay", "GET", biz_content=biz_content
    )
    notify_url = f"{settings.alipay_notify_url}/api/v1/pay/notify"

    return {
        "payUrl": f"{pay_url}&notify_url={notify_url}",
        "timeExpire": int(time_expire.timestamp() * 1000),
    }


async def handle_payment_notify(db: AsyncSession, form_data: dict) -> bool:
    """
    处理支付宝回调。
    对应 NestJS PayService.notify。
    """
    out_trade_no = form_data.get("out_trade_no")
    trade_no = form_data.get("trade_no")
    gmt_payment = form_data.get("gmt_payment")
    body_str = form_data.get("body", "{}")

    # 更新支付记录
    result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.out_trade_no == out_trade_no)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        return False

    payment.trade_no = trade_no
    payment.trade_status = TradeStatus.TRADE_SUCCESS
    payment.send_pay_time = datetime.now(timezone.utc)
    await db.flush()

    # 创建课程记录
    body = json.loads(body_str)
    course_record = CourseRecord(
        user_id=body["userId"],
        course_id=body["courseId"],
        is_purchased=True,
        payment_record_id=payment.id,
    )
    db.add(course_record)
    await db.flush()
    await db.commit()

    # Socket.IO 通知前端
    await emit_payment_success(body["userId"])

    return True
```

- [ ] **Step 15.3: 实现 routers/pay.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.pay import CreatePayDto
from app.services.pay import create_payment, handle_payment_notify

router = APIRouter(prefix="/api/v1/pay", tags=["pay"])


@router.post("/create")
async def create(data: CreatePayDto, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """创建支付订单。对应 NestJS POST /api/v1/pay/create（需要认证）"""
    try:
        result = await create_payment(db, data.model_dump(), user["userId"])
        return {"data": result, "code": 200, "message": "创建成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.api_route("/notify", methods=["GET", "POST"])
async def notify(request: Request, db: AsyncSession = Depends(get_db)):
    """支付宝回调。对应 NestJS ALL /api/v1/pay/notify"""
    if request.method == "POST":
        form_data = await request.form()
        data = dict(form_data)
    else:
        data = dict(request.query_params)

    await handle_payment_notify(db, data)
    return "success"
```

- [ ] **Step 15.4: 注册路由并验证**

```python
from app.routers import user, word_book, course, pay
app.include_router(pay.router)
```

验证：创建订单后返回 `payUrl`，支付宝回调后数据库中 `trade_status` 变为 `TRADE_SUCCESS`。

---

## 步骤 16: Learn — 获取单词 + 标记掌握

**目标:** 实现单词学习模块。

**Files:**
- Create: `server/app/schemas/learn.py`
- Create: `server/app/services/learn.py`
- Create: `server/app/routers/learn.py`
- Modify: `server/app/main.py`

**参考:** `serverOld/apps/server/src/learn/learn.service.ts`。

- [ ] **Step 16.1: 实现 schemas/learn.py**

```python
from pydantic import BaseModel


class SaveWordMasterDto(BaseModel):
    wordIds: list[str]
```

- [ ] **Step 16.2: 实现 services/learn.py**

```python
from nanoid import generate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, CourseRecord
from app.models.word_book import WordBook, WordBookRecord
from app.models.user import User


async def get_word_list(db: AsyncSession, course_id: str, user_id: str) -> list:
    """
    获取课程单词列表（排除已掌握的）。
    对应 NestJS LearnService.getWordList。
    """
    # 验证用户已购买课程
    result = await db.execute(
        select(CourseRecord)
        .where(
            CourseRecord.user_id == user_id,
            CourseRecord.course_id == course_id,
            CourseRecord.is_purchased == True,
        )
        .join(CourseRecord.course)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError("非法请求")

    course_type = record.course.value  # gk, zk, etc.

    # 查询未掌握的单词
    # 需要排除已有 WordBookRecord 的单词
    subquery = (
        select(WordBookRecord.word_id)
        .where(WordBookRecord.user_id == user_id)
        .scalar_subquery()
    )

    stmt = (
        select(WordBook)
        .where(
            getattr(WordBook, course_type) == True,
            WordBook.id.notin_(subquery),
        )
        .order_by(WordBook.frq.desc())
        .limit(10)
    )

    words_result = await db.execute(stmt)
    words = words_result.scalars().all()

    return [
        {
            "id": w.id,
            "word": w.word,
            "phonetic": w.phonetic,
            "definition": w.definition,
            "translation": w.translation,
            "pos": w.pos,
            "collins": w.collins,
            "oxford": w.oxford,
            "tag": w.tag,
            "bnc": w.bnc,
            "frq": w.frq,
            "exchange": w.exchange,
        }
        for w in words
    ]


async def save_word_master(db: AsyncSession, word_ids: list[str], user_id: str) -> dict:
    """
    标记单词为已掌握。
    对应 NestJS LearnService.saveWordMaster。
    """

    # 批量创建 WordBookRecord
    for word_id in word_ids:
        record = WordBookRecord(
            id=generate(size=20),
            word_id=word_id,
            user_id=user_id,
            is_master=True,
        )
        db.add(record)

    await db.flush()

    # 更新用户单词数量
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.word_number += len(word_ids)
        await db.flush()
        await db.commit()
        return {"wordNumber": user.word_number}

    await db.commit()
    return {"wordNumber": 0}
```

- [ ] **Step 16.3: 实现 routers/learn.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.learn import SaveWordMasterDto
from app.services.learn import get_word_list, save_word_master

router = APIRouter(prefix="/api/v1/learn", tags=["learn"])


@router.get("/word/{course_id}")
async def word_list(course_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取课程单词。对应 NestJS GET /api/v1/learn/word/:id"""
    try:
        result = await get_word_list(db, course_id, user["userId"])
        return {"data": result, "code": 200, "message": "查询成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/word/master")
async def master(data: SaveWordMasterDto, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """标记单词掌握。对应 NestJS POST /api/v1/learn/word/master"""
    result = await save_word_master(db, data.wordIds, user["userId"])
    return {"data": result, "code": 200, "message": "保存成功"}
```

- [ ] **Step 16.4: 注册路由并验证**

```python
from app.routers import user, word_book, course, pay, learn
app.include_router(learn.router)
```

```bash
# 获取单词（需要先登录获取 token）
curl -H "Authorization: Bearer <token>" http://localhost:3000/api/v1/learn/word/<courseId>

# 标记掌握
curl -X POST http://localhost:3000/api/v1/learn/word/master \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"wordIds":["id1","id2"]}'
```

---

## 步骤 17: Tracker — UV/PV/事件/性能/错误

**目标:** 实现全部 5 个 Tracker 接口。

**Files:**
- Create: `server/app/schemas/tracker.py`
- Create: `server/app/services/tracker.py`
- Create: `server/app/routers/tracker.py`
- Modify: `server/app/main.py`

**参考:** `serverOld/apps/server/src/tracker/tracker.service.ts`。

- [ ] **Step 17.1: 实现 schemas/tracker.py**

```python
from pydantic import BaseModel


class UvDto(BaseModel):
    anonymousId: str
    userId: str | None = None
    browser: str | None = None
    os: str | None = None
    device: str | None = None


class UpdateUvDto(BaseModel):
    visitorId: str
    userId: str


class PvDto(BaseModel):
    visitorId: str
    url: str
    referrer: str | None = None
    path: str


class EventDto(BaseModel):
    visitorId: str
    event: str
    payload: dict | None = None
    url: str | None = None


class PerformanceDto(BaseModel):
    visitorId: str
    fp: float | None = None
    fcp: float | None = None
    lcp: float | None = None
    inp: float | None = None
    cls: float | None = None


class ErrorDto(BaseModel):
    visitorId: str
    error: str
    message: str | None = None
    stack: str | None = None
    url: str | None = None
```

- [ ] **Step 17.2: 实现 services/tracker.py**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from nanoid import generate

from app.models.visitor import Visitor, PageView, TrackEvent, PerformanceEntry, ErrorEntry


async def upsert_visitor(db: AsyncSession, data: dict) -> str:
    """
    上报/更新访客（UV）。
    对应 NestJS TrackerService.uv。
    """
    result = await db.execute(
        select(Visitor).where(Visitor.anonymous_id == data["anonymousId"])
    )
    visitor = result.scalar_one_or_none()

    if visitor:
        # 更新
        visitor.user_id = data.get("userId")
        visitor.browser = data.get("browser")
        visitor.os = data.get("os")
        visitor.device = data.get("device")
    else:
        # 创建
        visitor = Visitor(
            id=generate(size=20),
            anonymous_id=data["anonymousId"],
            user_id=data.get("userId"),
            browser=data.get("browser"),
            os=data.get("os"),
            device=data.get("device"),
        )
        db.add(visitor)

    await db.flush()
    await db.commit()
    return visitor.id


async def update_visitor(db: AsyncSession, data: dict) -> None:
    """更新访客的 userId。对应 NestJS TrackerService.updateUv"""
    result = await db.execute(select(Visitor).where(Visitor.id == data["visitorId"]))
    visitor = result.scalar_one_or_none()
    if visitor:
        visitor.user_id = data["userId"]
        await db.flush()
        await db.commit()


async def record_pv(db: AsyncSession, data: dict) -> None:
    """记录页面访问。对应 NestJS TrackerService.pv"""
    pv = PageView(
        id=generate(size=20),
        visitor_id=data["visitorId"],
        url=data["url"],
        referrer=data.get("referrer"),
        path=data["path"],
    )
    db.add(pv)
    await db.flush()
    await db.commit()


async def record_event(db: AsyncSession, data: dict) -> None:
    """记录用户行为。对应 NestJS TrackerService.event"""
    event = TrackEvent(
        id=generate(size=20),
        visitor_id=data["visitorId"],
        event=data["event"],
        payload=data.get("payload"),
        url=data.get("url"),
    )
    db.add(event)
    await db.flush()
    await db.commit()


async def record_performance(db: AsyncSession, data: dict) -> None:
    """记录性能指标。对应 NestJS TrackerService.performance"""
    entry = PerformanceEntry(
        id=generate(size=20),
        visitor_id=data["visitorId"],
        fp=data.get("fp"),
        fcp=data.get("fcp"),
        lcp=data.get("lcp"),
        inp=data.get("inp"),
        cls=data.get("cls"),
    )
    db.add(entry)
    await db.flush()
    await db.commit()


async def record_error(db: AsyncSession, data: dict) -> None:
    """记录错误。对应 NestJS TrackerService.error"""
    entry = ErrorEntry(
        id=generate(size=20),
        visitor_id=data["visitorId"],
        error=data["error"],
        message=data.get("message"),
        stack=data.get("stack"),
        url=data.get("url"),
    )
    db.add(entry)
    await db.flush()
    await db.commit()
```

- [ ] **Step 17.3: 实现 routers/tracker.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.tracker import (
    UvDto, UpdateUvDto, PvDto, EventDto, PerformanceDto, ErrorDto,
)
from app.services.tracker import (
    upsert_visitor, update_visitor, record_pv, record_event, record_performance, record_error,
)

router = APIRouter(prefix="/api/v1/tracker", tags=["tracker"])


@router.post("/uv")
async def uv(data: UvDto, db: AsyncSession = Depends(get_db)):
    visitor_id = await upsert_visitor(db, data.model_dump())
    return {"data": visitor_id, "code": 200, "message": "上报成功"}


@router.post("/update-uv")
async def update_uv(data: UpdateUvDto, db: AsyncSession = Depends(get_db)):
    await update_visitor(db, data.model_dump())
    return {"data": True, "code": 200, "message": "更新成功"}


@router.post("/pv")
async def pv(data: PvDto, db: AsyncSession = Depends(get_db)):
    await record_pv(db, data.model_dump())
    return {"data": True, "code": 200, "message": "上报成功"}


@router.post("/event")
async def event(data: EventDto, db: AsyncSession = Depends(get_db)):
    await record_event(db, data.model_dump())
    return {"data": True, "code": 200, "message": "上报成功"}


@router.post("/performance")
async def performance(data: PerformanceDto, db: AsyncSession = Depends(get_db)):
    await record_performance(db, data.model_dump())
    return {"data": True, "code": 200, "message": "上报成功"}


@router.post("/error")
async def error(data: ErrorDto, db: AsyncSession = Depends(get_db)):
    await record_error(db, data.model_dump())
    return {"data": True, "code": 200, "message": "上报成功"}
```

- [ ] **Step 17.4: 注册路由并验证**

```python
from app.routers import user, word_book, course, pay, learn, tracker
app.include_router(tracker.router)
```

```bash
# UV
curl -X POST http://localhost:3000/api/v1/tracker/uv \
  -H "Content-Type: application/json" \
  -d '{"anonymousId":"test-fp-123","browser":"Chrome","os":"Windows","device":"desktop"}'

# PV
curl -X POST http://localhost:3000/api/v1/tracker/pv \
  -H "Content-Type: application/json" \
  -d '{"visitorId":"<uv返回的id>","url":"http://localhost:8080/","path":"/"}'
```

---

## 步骤 18: AI FastAPI 应用 + Prompt 列表

**目标:** 创建独立的 AI FastAPI 应用，实现 Prompt 列表接口。

**Files:**
- Create: `server/ai/main.py`
- Create: `server/ai/config.py`
- Create: `server/ai/routers/__init__.py`
- Create: `server/ai/routers/prompt.py`
- Create: `server/ai/services/__init__.py`
- Create: `server/ai/services/prompt.py`

**参考:** `serverOld/apps/ai/src/prompt/prompt.mode.ts` 和 `prompt.service.ts`。

- [ ] **Step 18.1: 实现 ai/config.py**

```python
from pydantic_settings import BaseSettings
from pydantic import Field


class AISettings(BaseSettings):
    deepseek_api_key: str = Field(alias="DEEPSEEK_API_KEY")
    deepseek_api_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_API_MODEL")
    deepseek_reasoner_api_model: str = Field(
        default="deepseek-reasoner", alias="DEEPSEEK_REASONER_API_MODEL"
    )
    ai_database_url: str = Field(alias="AI_DATABASE_URL")
    bocha_search_url: str = Field(alias="BOCHA_SEARCH_URL")
    bocha_api_key: str = Field(alias="BOCHA_API_KEY")
    email_host: str = Field(alias="EMAIL_HOST")
    email_port: int = Field(alias="EMAIL_PORT")
    email_use_ssl: bool = Field(default=False, alias="EMAIL_USE_SSL")
    email_user: str = Field(alias="EMAIL_USER")
    email_password: str = Field(alias="EMAIL_PASSWORD")
    email_from: str = Field(alias="EMAIL_FROM")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


ai_settings = AISettings()
```

- [ ] **Step 18.2: 实现 ai/services/prompt.py**

```python
# 对应 serverOld/apps/ai/src/prompt/prompt.mode.ts

CHAT_MODES = [
    {
        "role": "normal",
        "prompt": "你是一个女仆请根据用户的对话内容，给出相应的回答，请用中文回答",
        "label": "💬 智能助手",
        "id": "1",
    },
    {
        "role": "master",
        "prompt": "你是一个英语大师，这是一个英语学习的对话，根据用户的对话内容，给出相应的回答(使用专业术语)，请用英文回答",
        "label": "🎓 英语大师",
        "id": "2",
    },
    {
        "role": "business",
        "prompt": "你是一个商务英语专家，这是一个商务英语的对话，根据用户的对话内容，给出相应的回答(使用商务英语专业术语)，请用中文回答",
        "label": "💼 商务英语",
        "id": "3",
    },
    {
        "role": "qilinge",
        "prompt": "你是一个喜欢装逼，天马行空，说话不着边际的一个人，容易暴怒，请根据用户的对话内容，给出相应的回答(使用麒麟哥的语气)，需要一点发癫，发疯，并且你从不道歉，请用中文回答",
        "label": "🐉 麒麟哥",
        "id": "4",
    },
    {
        "role": "xiaoman",
        "prompt": "你是一个知名程序员，这是一个程序员学习的对话，根据用户的对话内容，给出相应的回答(使用程序员专业术语)，请用中文回答",
        "label": "💻 小满模式",
        "id": "5",
    },
]


def get_prompt_list() -> list:
    """返回 prompt 列表（不含 prompt 字段，只返回 id/label/role）"""
    return [{"id": m["id"], "label": m["label"], "role": m["role"]} for m in CHAT_MODES]


def get_prompt_by_role(role: str) -> dict | None:
    """根据 role 获取完整的 prompt 对象"""
    return next((m for m in CHAT_MODES if m["role"] == role), None)
```

- [ ] **Step 18.3: 实现 ai/routers/prompt.py**

```python
from fastapi import APIRouter

from ai.services.prompt import get_prompt_list

router = APIRouter(prefix="/ai/v1/prompt", tags=["prompt"])


@router.get("/list")
async def list_prompts():
    """Prompt 列表。对应 NestJS GET /ai/v1/prompt/list"""
    result = get_prompt_list()
    return {"data": result, "code": 200, "message": "查询成功"}
```

- [ ] **Step 18.4: 实现 ai/main.py**

```python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ai.routers import prompt
from app.middleware import response_envelope_middleware, exception_handler

ai_app = FastAPI(title="English AI Server", version="0.1.0")

# 注册中间件
ai_app.middleware("http")(response_envelope_middleware)
ai_app.add_exception_handler(StarletteHTTPException, exception_handler)
ai_app.add_exception_handler(RequestValidationError, exception_handler)

# 注册路由
ai_app.include_router(prompt.router)


@ai_app.get("/")
async def root():
    return {"message": "ai access success"}
```

- [ ] **Step 18.5: 验证 AI 服务**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run uvicorn ai.main:ai_app --port 3001 &
sleep 2

curl http://localhost:3001/ai/v1/prompt/list
```

预期输出：
```json
{
  "data": [
    {"id": "1", "label": "💬 智能助手", "role": "normal"},
    {"id": "2", "label": "🎓 英语大师", "role": "master"},
    ...
  ],
  "code": 200,
  "message": "查询成功"
}
```

---

## 步骤 19: AI 聊天 — LangChain + DeepSeek + SSE

**目标:** 实现 SSE 流式聊天、深度思考、联网搜索、对话历史。

**Files:**
- Create: `server/ai/services/llm.py`
- Create: `server/ai/services/chat.py`
- Create: `server/ai/routers/chat.py`
- Modify: `server/ai/main.py`

**参考:** `serverOld/apps/ai/src/llm/llm.config.ts` 和 `chat/chat.service.ts`。

- [ ] **Step 19.1: 实现 ai/services/llm.py**

```python
import httpx
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from ai.config import ai_settings


def create_deepseek() -> ChatDeepSeek:
    """普通对话模型"""
    return ChatDeepSeek(
        api_key=ai_settings.deepseek_api_key,
        model=ai_settings.deepseek_api_model,
        temperature=1.3,
        max_tokens=4396,
        streaming=True,
    )


def create_deepseek_reasoner() -> ChatDeepSeek:
    """深度思考模型"""
    return ChatDeepSeek(
        api_key=ai_settings.deepseek_api_key,
        model=ai_settings.deepseek_reasoner_api_model,
        temperature=1.3,
        max_tokens=18000,
        streaming=True,
    )


async def create_checkpoint() -> AsyncPostgresSaver:
    """初始化 LangGraph checkpointer"""
    checkpointer = AsyncPostgresSaver.from_conn_string(ai_settings.ai_database_url)
    await checkpointer.setup()
    return checkpointer


async def create_bocha_search(query: str, count: int = 10) -> str:
    """调用 Bocha 搜索 API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            ai_settings.bocha_search_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ai_settings.bocha_api_key}",
            },
            json={"query": query, "count": count, "summary": True},
        )
        data = response.json()
        values = data.get("data", {}).get("webPages", {}).get("value", [])
        prompt = "\n".join(
            f"""
       标题：{item.get('name', '')}
       链接：{item.get('url', '')}
       摘要：{item.get('summary', '').replace(chr(10), '')}
       网站名称：{item.get('siteName', '')}
       网站logo：{item.get('siteIcon', '')}
       发布时间：{item.get('dateLastCrawled', '')}
    """
            for item in values
        )
        return prompt
```

- [ ] **Step 19.2: 实现 ai/services/chat.py**

```python
import json

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from ai.services.llm import create_deepseek, create_deepseek_reasoner, create_checkpoint, create_bocha_search
from ai.services.prompt import get_prompt_by_role


# 全局 checkpointer（启动时初始化）
_checkpointer = None


async def get_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = await create_checkpoint()
    return _checkpointer


async def stream_chat(data: dict):
    """
    SSE 流式聊天。
    对应 NestJS ChatService.streamCompletion。
    """
    role = data.get("role", "normal")
    content = data.get("content", "")
    deep_think = data.get("deepThink", False)
    web_search = data.get("webSearch", False)
    user_id = data.get("userId", "")

    prompt_obj = get_prompt_by_role(role)
    if not prompt_obj:
        raise ValueError("模式不存在")

    prompt = prompt_obj["prompt"]

    # 联网搜索增强
    if web_search:
        search_results = await create_bocha_search(content)
        prompt += f"请根据以下搜索结果回答问题：{search_results}(并且返回你参考的网站名称)，用户问题：{content}"

    # 选择模型
    model = create_deepseek_reasoner() if deep_think else create_deepseek()

    # 创建 agent
    checkpointer = await get_checkpointer()
    agent = create_react_agent(
        model=model,
        tools=[],
        checkpointer=checkpointer,
    )

    # 流式输出
    thread_id = f"{user_id}-{role}"
    async for event in agent.astream_events(
        {"messages": [HumanMessage(content=content)]},
        config={"configurable": {"thread_id": thread_id}},
        version="v2",
    ):
        kind = event.get("event")
        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk:
                # 深度思考内容
                reasoning = getattr(chunk, "additional_kwargs", {}).get("reasoning_content", "")
                if reasoning:
                    yield f"data: {json.dumps({'content': reasoning, 'role': 'ai', 'type': 'reasoning'}, ensure_ascii=False)}\n\n"
                # 普通内容
                content_text = chunk.content if hasattr(chunk, "content") else ""
                if content_text:
                    yield f"data: {json.dumps({'content': content_text, 'role': 'ai', 'type': 'chat'}, ensure_ascii=False)}\n\n"


async def get_chat_history(user_id: str, role: str) -> list:
    """
    获取对话历史。
    对应 NestJS ChatService.findAll。
    """
    checkpointer = await get_checkpointer()
    thread_id = f"{user_id}-{role}"

    try:
        state = await checkpointer.get({"configurable": {"thread_id": thread_id}})
        if not state or not state.channel_values.get("messages"):
            return []

        messages = state.channel_values["messages"]
        return [
            {
                "content": msg.content,
                "role": msg.type,
                "reasoning": getattr(msg, "additional_kwargs", {}).get("reasoning_content"),
            }
            for msg in messages
        ]
    except Exception:
        return []
```

- [ ] **Step 19.3: 实现 ai/routers/chat.py**

```python
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from ai.services.chat import stream_chat, get_chat_history

router = APIRouter(prefix="/ai/v1/chat", tags=["chat"])


@router.post("")
async def chat(data: dict):
    """
    SSE 流式聊天。对应 NestJS POST /ai/v1/chat。
    """
    return StreamingResponse(
        stream_chat(data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/history")
async def history(userId: str = Query(...), role: str = Query(...)):
    """对话历史。对应 NestJS GET /ai/v1/chat/history"""
    result = await get_chat_history(userId, role)
    return {"data": result, "code": 200, "message": "查询成功"}
```

- [ ] **Step 19.4: 注册路由到 ai/main.py**

```python
from ai.routers import prompt, chat
ai_app.include_router(chat.router)
```

- [ ] **Step 19.5: 验证 AI 聊天**

```bash
# 流式聊天
curl -X POST http://localhost:3001/ai/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"role":"normal","content":"hello","deepThink":false,"webSearch":false,"userId":"test"}'

# 对话历史
curl "http://localhost:3001/ai/v1/chat/history?userId=test&role=normal"
```

预期：流式输出 `data: {"content":"...","role":"ai","type":"chat"}` 格式。

---

## 步骤 20: AI 摘要 — APScheduler + 邮件

**目标:** 实现定时单词记忆报告生成和邮件发送。

**Files:**
- Create: `server/ai/services/digest.py`
- Modify: `server/ai/main.py`

**参考:** `serverOld/apps/ai/src/digest/digest.service.ts`。

- [ ] **Step 20.1: 实现 ai/services/digest.py**

```python
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from langgraph.prebuilt import create_react_agent
from markdown2 import markdown

from app.database import async_session
from app.models.user import User
from app.models.word_book import WordBookRecord
from ai.services.llm import create_deepseek
from shared.email_client import send_email

scheduler = AsyncIOScheduler()


async def handle_email_digest():
    """
    定时任务：扫描用户，生成 AI 报告，延迟发送邮件。
    对应 NestJS DigestService.handleEmailDigest。
    """
    print("定时任务执行了")

    async with async_session() as db:
        # 筛选高质量用户
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        result = await db.execute(
            select(User).where(
                User.is_timing_task == True,
                User.timing_task_time != "",
                User.email.isnot(None),
                User.word_book_records.any(
                    WordBookRecord.created_at >= today_start,
                    WordBookRecord.created_at < tomorrow_start,
                ),
            )
        )
        users = result.scalars().all()

        for user in users:
            # 查询用户今日单词记录
            records_result = await db.execute(
                select(WordBookRecord)
                .where(
                    WordBookRecord.user_id == user.id,
                    WordBookRecord.created_at >= today_start,
                    WordBookRecord.created_at < tomorrow_start,
                )
            )
            records = records_result.scalars().all()

            if not records:
                continue

            # 生成报告
            model = create_deepseek()
            agent = create_react_agent(model=model, tools=[])

            word_count = user.word_number
            report_prompt = f"用户 {user.name} 今日学习了 {len(records)} 个单词，累计掌握 {word_count} 个单词。请生成一份简短的单词记忆报告。"

            try:
                result = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": report_prompt}]}
                )
                content = result["messages"][-1].content
            except Exception as e:
                print(f"AI report generation failed: {e}")
                continue

            if content:
                html = markdown(content)

                # 计算延迟发送时间
                try:
                    hour, minute, second = map(int, user.timing_task_time.split(":"))
                    target = datetime.now().replace(hour=hour, minute=minute, second=second, microsecond=0)
                    delay = (target - datetime.now()).total_seconds()
                    if delay < 0:
                        delay = 0
                except ValueError:
                    delay = 0

                # 延迟发送邮件（简单实现：直接等待后发送）
                # 生产环境应使用 APScheduler 的 date trigger
                if delay > 0:
                    scheduler.add_job(
                        send_email,
                        "date",
                        run_date=datetime.now() + timedelta(seconds=delay),
                        args=[user.email, "单词记忆报告", html],
                    )
                else:
                    await send_email(user.email, "单词记忆报告", html)


def start_scheduler():
    """启动定时任务调度器"""
    scheduler.add_job(
        handle_email_digest,
        CronTrigger(hour=0, minute=0, second=0),  # 每天 00:00:00
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()
    print("APScheduler started: daily digest at 00:00:00")
```

- [ ] **Step 20.2: 在 ai/main.py 中启动定时任务**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai.services.digest import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动定时任务"""
    start_scheduler()
    yield
    # 关闭时清理


ai_app = FastAPI(title="English AI Server", version="0.1.0", lifespan=lifespan)
# ... 其余代码 ...
```

- [ ] **Step 20.3: 验证定时任务**

```bash
cd "c:/Users/21943/Desktop/project/小组项目/english/server"
uv run uvicorn ai.main:ai_app --port 3001
```

预期：启动日志中出现 `APScheduler started: daily digest at 00:00:00`。

手动触发测试：
```bash
# 在 Python 控制台中手动调用
uv run python -c "
import asyncio
from ai.services.digest import handle_email_digest
asyncio.run(handle_email_digest())
"
```

---

## 收尾步骤

### ClickHouse 客户端

**Files:**
- Create: `server/shared/clickhouse_client.py`

```python
import clickhouse_connect
from app.config import settings


class ClickHouseClient:
    def __init__(self):
        self.client = None

    def connect(self):
        if settings.clickhouse_url:
            self.client = clickhouse_connect.get_client(
                host=settings.clickhouse_url,
                username=settings.clickhouse_username,
                password=settings.clickhouse_password,
                database=settings.clickhouse_database,
            )

    def get_client(self):
        return self.client


clickhouse_client = ClickHouseClient()
```

### 根目录启动脚本

在 `server/pyproject.toml` 中添加 scripts：

```toml
[project.scripts]
start-server = "app.main:app"
start-ai = "ai.main:ai_app"
```

或在根目录 `package.json` 中更新 scripts：

```json
{
  "scripts": {
    "server": "cd server && uv run uvicorn app.main:app --port 3000 --reload",
    "ai": "cd server && uv run uvicorn ai.main:ai_app --port 3001 --reload",
    "all": "concurrently \"pnpm run web\" \"pnpm run server\" \"pnpm run ai\""
  }
}
```

### 前端联调验证清单

- [ ] 注册 + 登录 → 返回 token → 设置到 store
- [ ] Token 过期 → 自动刷新 → 请求重放
- [ ] 上传头像 → MinIO 存储 → 显示头像
- [ ] 更新用户资料 → 数据库更新
- [ ] 单词本查询 → 分页 + 标签过滤
- [ ] 课程列表 → 显示价格
- [ ] 购买课程 → 支付宝页面 → 回调 → Socket.IO 通知 → 关闭弹窗
- [ ] 已购课程列表
- [ ] 单词学习 → 拼写练习 → 标记掌握
- [ ] AI 聊天 → SSE 流式输出 → 深度思考 → 联网搜索
- [ ] 对话历史 → 切换角色
- [ ] Tracker → UV/PV/事件/性能/错误上报


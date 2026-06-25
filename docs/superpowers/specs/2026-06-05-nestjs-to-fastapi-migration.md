# NestJS → FastAPI 全量迁移设计文档

## 概述

将后端从 NestJS (TypeScript) 全量迁移到 Python FastAPI，AI 服务从 LangChain JS 切换到 Python LangChain。前端（Vue 3）完全不动，API 接口路径和响应格式保持兼容。

## 关键决策

| 决策 | 选择 | 理由 |
|---|---|---|
| 迁移策略 | 一次性全量替换（方案 A） | 统一技术栈，避免过渡期两套后端并存 |
| 包管理 | uv | 快速、隔离虚拟环境、锁定依赖版本 |
| 数据库 ORM | SQLAlchemy + Alembic | Python 生态最成熟 |
| 实时通信 | python-socketio | 与前端 Socket.IO 客户端兼容 |
| 定时任务 | APScheduler | 替代 BullMQ + Redis，更轻量 |
| 前端兼容 | 完全不动 | API 路径、端口、响应格式保持一致 |

## 当前架构（NestJS）

```
server/
├── apps/server/          # 主 API（端口 3000，前缀 /api）
│   └── src/
│       ├── user/         # 注册/登录/头像/资料
│       ├── word-book/    # 单词查询
│       ├── course/       # 课程列表/已购
│       ├── pay/          # 支付宝支付 + 回调
│       ├── learn/        # 单词学习/掌握
│       ├── tracker/      # UV/PV/事件/性能/错误
│       ├── socket/       # Socket.IO 实时通知
│       └── auth/         # JWT 生成
├── apps/ai/              # AI 服务（端口 3001，前缀 /ai）
│   └── src/
│       ├── chat/         # SSE 流式聊天 + 对话历史
│       ├── prompt/       # 角色 prompt 列表
│       ├── digest/       # 定时邮件摘要
│       └── llm/          # DeepSeek + Bocha 配置
├── libs/shared/          # 共享库（@Global）
│   └── src/
│       ├── prisma/       # PrismaService
│       ├── auth/         # AuthGuard
│       ├── minio/        # MinIO 客户端
│       ├── pay/          # Alipay 客户端
│       ├── email/        # Email 客户端
│       ├── clickhouse/   # ClickHouse 客户端
│       ├── response/     # ResponseService
│       └── interceptor/  # 全局拦截器 + 异常过滤器
└── prisma/
    └── schema.prisma     # 11 个模型
```

## 目标架构（FastAPI）

```
server/
├── pyproject.toml              # uv 项目配置 + 依赖声明
├── uv.lock                     # 锁定依赖版本
├── .venv/                      # uv 自动创建的虚拟环境
├── alembic.ini
├── alembic/
├── .env                        # 环境变量（与当前格式兼容）
├── app/                        # 主 API 应用（端口 3000）
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口 + 路由注册
│   ├── config.py               # pydantic-settings 配置
│   ├── database.py             # SQLAlchemy async engine + Session
│   ├── models/                 # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── word_book.py
│   │   ├── course.py
│   │   ├── payment.py
│   │   ├── learn.py
│   │   └── visitor.py
│   ├── schemas/                # Pydantic 请求/响应模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── word_book.py
│   │   ├── course.py
│   │   ├── pay.py
│   │   ├── learn.py
│   │   └── tracker.py
│   ├── dependencies.py         # 依赖注入（Auth、DB Session）
│   ├── middleware.py           # 全局响应信封 + 异常过滤器
│   ├── routers/                # API 路由（对应原 controller）
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── word_book.py
│   │   ├── course.py
│   │   ├── pay.py
│   │   ├── learn.py
│   │   └── tracker.py
│   └── services/               # 业务逻辑（对应原 service）
│       ├── __init__.py
│       ├── auth.py
│       ├── user.py
│       ├── word_book.py
│       ├── course.py
│       ├── pay.py
│       ├── learn.py
│       └── tracker.py
├── ai/                         # AI 服务（端口 3001）
│   ├── __init__.py
│   ├── main.py                 # 独立 FastAPI 应用
│   ├── config.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py             # SSE 流式聊天
│   │   └── prompt.py           # Prompt 列表
│   └── services/
│       ├── __init__.py
│       ├── chat.py             # LangChain agent + DeepSeek
│       ├── llm.py              # LLM 配置
│       └── digest.py           # 定时摘要
└── shared/                     # 共享客户端
    ├── __init__.py
    ├── minio_client.py
    ├── alipay_client.py
    ├── email_client.py
    └── clickhouse_client.py
```

## 依赖清单（pyproject.toml）

```toml
[project]
name = "english-server"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0",
    "alembic>=1.14",
    "asyncpg>=0.30",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "python-jose[cryptography]>=3.3",   # JWT 生成/验证
    "minio>=7.2",                        # MinIO SDK
    "alipay-sdk-python>=4.0",           # 支付宝 SDK
    "python-socketio[asyncio]>=5.11",   # Socket.IO（兼容客户端 v4）
    "aiosmtplib>=3.0",                  # 异步 SMTP 发邮件
    "markdown2>=2.5",                   # markdown 转 HTML
    "langchain>=0.3",
    "langchain-deepseek>=0.1",          # DeepSeek ChatModel
    "langgraph>=0.2",
    "langgraph-checkpoint-postgres>=2.0",
    "apscheduler>=3.10",                # 定时任务
    "clickhouse-connect>=0.8",          # ClickHouse
    "nanoid>=2.0",                      # 生成 trade number
    "httpx>=0.28",                      # HTTP 客户端（Bocha 搜索）
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

> **注意**：
> - `langchain-deepseek` 已在 PyPI 上，若安装失败可 fallback 到 `langchain-openai` + 自定义 `base_url`
> - `alipay-sdk-python` 对应 npm 的 `alipay-sdk`，API 略有不同但功能一致
> - `aiosmtplib` 是 Python 标准库 `smtplib` 的异步版，无需额外依赖
> - 不再需要 `redis`，APScheduler 直接用内存调度（如需持久化可加 `apscheduler[redis]`）

## API 接口兼容性

所有接口保持相同的路径、方法、请求体和响应格式：

### 响应信封

```json
{
  "timestamp": 1234567890,
  "path": "/api/v1/user/login",
  "message": "success",
  "code": 200,
  "success": true,
  "data": { ... }
}
```

### 完整接口列表

| 方法 | 路径 | 认证 | 对应模块 |
|---|---|---|---|
| POST | /api/v1/user/register | 否 | User |
| POST | /api/v1/user/login | 否 | User |
| POST | /api/v1/user/refresh-token | 否 | User |
| POST | /api/v1/user/upload-avatar | 否 | User |
| POST | /api/v1/user/update-user | 是 | User |
| GET | /api/v1/word-book | 否 | WordBook |
| GET | /api/v1/course/list | 否 | Course |
| GET | /api/v1/course/my | 是 | Course |
| POST | /api/v1/pay/create | 是 | Pay |
| ALL | /api/v1/pay/notify | 否 | Pay |
| GET | /api/v1/learn/word/:id | 是 | Learn |
| POST | /api/v1/learn/word/master | 是 | Learn |
| POST | /api/v1/tracker/uv | 否 | Tracker |
| POST | /api/v1/tracker/update-uv | 否 | Tracker |
| POST | /api/v1/tracker/pv | 否 | Tracker |
| POST | /api/v1/tracker/event | 否 | Tracker |
| POST | /api/v1/tracker/performance | 否 | Tracker |
| POST | /api/v1/tracker/error | 否 | Tracker |
| POST | /ai/v1/chat | 否 | AI Chat |
| GET | /ai/v1/chat/history | 否 | AI Chat |
| GET | /ai/v1/prompt/list | 否 | AI Prompt |

## 数据库模型映射

从 Prisma schema 迁移到 SQLAlchemy：

| Prisma 模型 | SQLAlchemy 模型 | 表名 |
|---|---|---|
| User | User | user |
| WordBook | WordBook | word_book |
| WordBookRecord | WordBookRecord | word_book_record |
| Course | Course | course |
| CourseRecord | CourseRecord | course_record |
| PaymentRecord | PaymentRecord | payment_record |
| Visitor | Visitor | visitor |
| PageView | PageView | page_view |
| TrackEvent | TrackEvent | track_event |
| PerformanceEntry | PerformanceEntry | performance_entry |
| ErrorEntry | ErrorEntry | error_entry |

TradeStatus 枚举：NOT_PAY, WAIT_BUYER_PAY, TRADE_CLOSED, TRADE_SUCCESS, TRADE_FINISHED

### 字段类型映射

| Prisma 类型 | SQLAlchemy 类型 | 备注 |
|---|---|---|
| `String @id @default(cuid())` | `String(30), primary_key=True` | Python 端用 `nanoid` 生成 cuid |
| `String` | `String` | — |
| `String?` | `String, nullable=True` | — |
| `Int @default(0)` | `Integer, default=0` | — |
| `Boolean @default(false)` | `Boolean, default=False` | — |
| `DateTime @default(now())` | `DateTime, server_default=func.now()` | — |
| `DateTime @updatedAt` | `DateTime, onupdate=func.now()` | — |
| `DateTime?` | `DateTime, nullable=True` | — |
| `Decimal` | `Numeric(10, 2)` | 价格字段，与 Prisma Decimal 兼容 |
| `Json?` | `JSON, nullable=True` | TrackEvent payload |
| `Float?` | `Float, nullable=True` | PerformanceEntry 指标 |

### 索引与约束迁移

Prisma schema 中的索引/约束必须在 SQLAlchemy 模型中一一对应：

- `@@unique([userId, wordId])` → `UniqueConstraint('user_id', 'word_id')`
- `@@unique([userId, courseId])` → `UniqueConstraint('user_id', 'course_id')`
- `@unique` (anonymousId, phone, email) → `unique=True`
- `@@index([...])` → `Index(...)`
- 所有外键的 `onDelete: Cascade` → `ForeignKey(..., ondelete='CASCADE')`

## 认证系统

- JWT 双 token 机制保持不变
- accessToken: 短过期（当前 10 秒，生产环境可调）
- refreshToken: 7 天过期
- tokenType 字段区分 access/refresh
- FastAPI 使用 `Depends()` 替代 NestJS 的 `@UseGuards(AuthGuard)`
- 密码：前端用 MD5 哈希后发送，后端直接比较 MD5 值（无额外 hashing）。迁移时需保持一致，否则用户无法登录

## AI 服务

- 独立 FastAPI 进程，端口 3001
- Python LangChain + langchain-deepseek 替代 JS 版
- langgraph-checkpoint-postgres 替代 JS 版 PostgresSaver
- thread_id 隔离：`${userId}-${role}`
- SSE 流式：FastAPI 的 `StreamingResponse` + `text/event-stream`
- 深度思考：DeepSeek reasoner 模型（reasoning_content 字段）
- 联网搜索：Bocha Search API
- 定时摘要：APScheduler cron 替代 BullMQ

### SSE 格式兼容性

前端用 `@microsoft/fetch-event-source` 解析，Python 端必须严格遵守 SSE 规范：

```
data: {"role":"ai","content":"你好","type":"chat"}\n\n
data: {"role":"ai","content":"思考过程...","type":"reasoning"}\n\n
```

关键要求：
- 每条消息以 `data: ` 开头（注意 `data:` 后有空格）
- 每条消息以 `\n\n`（双换行）结尾
- JSON 中不能有换行符（用 `json.dumps(ensure_ascii=False)` 单行输出）
- Content-Type 必须是 `text/event-stream`
- Cache-Control: `no-cache`
- Connection: `keep-alive`

### Socket.IO 兼容性

- 前端：`socket.io-client@4.8.3`
- Python 端：`python-socketio[asyncio]>=5.x`（Socket.IO protocol v5，兼容客户端 v4）
- 命名空间：默认 `/`
- 事件名：`paymentSuccess`（与前端 `socket.on('paymentSuccess')` 一致）
- 连接参数：前端通过 `query: { userId }` 传递，Python 端从 `environ['QUERY_STRING']` 解析

## 实施步骤（20 步）

### 基础设施层

1. 项目骨架：uv init、pyproject.toml、目录结构
2. 配置模块：pydantic-settings 读 .env
3. 数据库连接：SQLAlchemy async engine + Session
4. SQLAlchemy ORM 模型：全部 11 个
5. Alembic 迁移：初始化 + 初始迁移
6. 全局中间件：响应信封 + 异常过滤器
7. MinIO 客户端
8. JWT 认证：token 生成 + 验证依赖
9. Alipay 客户端

### 主 API 模块

10. User — 注册 + 登录
11. User — refresh-token + upload-avatar + update-user
12. WordBook — 分页查询 + 标签过滤
13. Course — 课程列表 + 我的课程
14. Email 客户端 + Socket.IO
15. Pay — 创建订单 + 回调 + Socket.IO 通知
16. Learn — 获取单词 + 标记掌握
17. Tracker — UV/PV/事件/性能/错误

### AI 服务

18. AI FastAPI 应用 + Prompt 列表
19. AI 聊天：LangChain + DeepSeek + SSE + 深度思考 + 联网搜索
20. AI 摘要：APScheduler + 邮件

### 收尾

- ClickHouse 客户端
- 根目录启动脚本
- 前端联调验证

## 环境变量兼容

`.env` 文件格式保持不变，Python 端用 pydantic-settings 读取：

```
DATABASE_URL=postgresql://...
SECRET_KEY=...
MINIO_ENDPOINT=localhost
MINIO_PORT=9000
MINIO_USE_SSL=false
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET=...
DEEPSEEK_API_KEY=...
DEEPSEEK_API_MODEL=...
DEEPSEEK_REASONER_API_MODEL=...
AI_DATABASE_URL=postgresql://...
BOCHA_SEARCH_URL=...
BOCHA_API_KEY=...
ALIPAY_APP_ID=...
ALIPAY_PRIVATE_KEY=...
ALIPAY_PUBLIC_KEY=...
ALIPAY_GATEWAY=...
ALIPAY_NOTIFY_URL=...
EMAIL_HOST=...
EMAIL_PORT=...
EMAIL_USE_SSL=...
EMAIL_USER=...
EMAIL_PASSWORD=...
EMAIL_FROM=...
REDIS_HOST=...
REDIS_PORT=...
CLICKHOUSE_URL=...
CLICKHOUSE_USERNAME=...
CLICKHOUSE_PASSWORD=...
CLICKHOUSE_DATABASE=...
```

## 风险与应对策略

| 风险 | 影响 | 应对策略 |
|---|---|---|
| **密码兼容** | 用户无法登录 | 前端 MD5 哈希 → 后端直接比较 MD5 值，不做额外 hashing。数据库已有密码不变 |
| **Alembic 迁移失败** | 数据丢失或表结构不一致 | 先用 `alembic revision --autogenerate` 生成迁移脚本，人工审核 diff 确认无误后再 `upgrade`。在测试库先验证 |
| **SSE 格式不兼容** | AI 聊天断流或解析错误 | 严格按 `data: {json}\n\n` 格式输出，用 `@microsoft/fetch-event-source` 的解析逻辑做端到端测试 |
| **Socket.IO 版本不匹配** | 支付通知收不到 | Python 端用 `python-socketio>=5.x`（protocol v5），与前端 `socket.io-client@4.x` 兼容。连接后立即测试 `paymentSuccess` 事件 |
| **Prisma 生成代码** | 不再需要 | 迁移完成后删除 `server/libs/shared/src/generated/prisma/` |
| **Monorepo 结构** | pnpm 工作区报错 | 重命名 `server` → `serverOld` 后更新 `pnpm-workspace.yaml`，移除 `server` 条目 |
| **AI 模块初始化异常** | DeepSeek 连接失败 | 在 `ai/services/llm.py` 中加 try-catch，启动时验证 API key 有效性，失败时记录日志但不阻塞主服务启动 |
| **依赖安装失败** | 环境搭建卡住 | `langchain-deepseek` 已在 PyPI 上，但若安装失败可 fallback 到 `langchain-openai` + 自定义 base_url |

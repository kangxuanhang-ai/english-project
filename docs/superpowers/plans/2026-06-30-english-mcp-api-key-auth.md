# English MCP 用户 API Key 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户在 Web 设置页生成 MCP API Key，任意用户通过 Claude Code HTTP MCP（`ENGLISH-MCP-API-KEY` Header）连接托管服务，个性化 tool 绑定登录用户。

**Architecture:** 主 API（:3000）负责 Key CRUD + 返回 Claude 配置片段；`mcp_api_key` 表存 hash；MCP HTTP（:3002）用 Starlette 中间件校验 Header → ContextVar → 现有 `tools_handlers`；HTTP 模式**禁止** `.env` demo 回退。

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Vue 3, Element Plus, FastMCP Streamable HTTP, Starlette Middleware

**Spec:** `docs/superpowers/specs/2026-06-30-english-mcp-api-key-auth-design.md`

---

## 文件总览

| Phase | 新建 | 修改 |
|-------|------|------|
| A | `app/models/mcp_api_key.py`, `app/services/mcp_api_key.py`, `app/schemas/mcp_keys.py`, `app/routers/mcp_keys.py`, `alembic/versions/*`, `scripts/smoke_mcp_keys_api.py` | `app/models/__init__.py`, `app/config.py`, `app/main.py`, `.env.example` |
| B | `english_mcp/context.py`, `english_mcp/middleware.py`, `english_mcp/runtime.py`, `scripts/smoke_mcp_keys.py` | `english_mcp/auth.py`, `english_mcp/http_server.py`, `english_mcp/server.py`, `english_mcp/tools_handlers.py`, `english_mcp/rate_limit.py`, `english_mcp/config.py` |
| C | `apps/web/src/apis/mcp-keys/index.ts`, `packages/common/mcp/index.ts` | `apps/web/src/views/Setting/index.vue` |
| D | `docs/mcp-claude-setup.md` | `docs/deploy/nginx.example.conf`, `.mcp.json.example`, `server/.env.example`, `AGENTS.md`（可选一句） |

---

# Phase A — 数据库 + Key CRUD API

### Task A.1: Model + Alembic 迁移

**Files:**
- Create: `server/app/models/mcp_api_key.py`
- Modify: `server/app/models/__init__.py`
- Create: `server/alembic/versions/<rev>_add_mcp_api_key.py`（autogenerate）

- [ ] **Step 1: 创建 ORM 模型**

```python
# server/app/models/mcp_api_key.py
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class McpApiKey(Base):
    __tablename__ = "mcp_api_key"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(30), ForeignKey("user.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64), default="")
    key_prefix: Mapped[str] = mapped_column(String(24))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 2: 在 `app/models/__init__.py` 导出 `McpApiKey`**

- [ ] **Step 3: 生成并应用迁移**

```powershell
cd server
uv run alembic revision --autogenerate -m "add mcp_api_key table"
uv run alembic upgrade head
```

Expected: `mcp_api_key` 表存在，`key_hash` UNIQUE。

- [ ] **Step 4: Commit** `feat(db): add mcp_api_key table`

---

### Task A.2: mcp_api_key Service

**Files:**
- Create: `server/app/services/mcp_api_key.py`

- [ ] **Step 1: 实现 Key 生成与 hash**

```python
import hashlib
import hmac
import json
import secrets

KEY_PREFIX = "en_mcp_live_"
MAX_KEYS_PER_USER = 3

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

def _generate_raw_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)

def build_claude_config(raw_key: str, public_url: str) -> dict:
    return {
        "mcpServers": {
            "english": {
                "type": "http",
                "url": public_url.rstrip("/"),
                "headers": {"ENGLISH-MCP-API-KEY": raw_key},
                "timeout": 60000,
            }
        }
    }
```

- [ ] **Step 2: 实现 `create_key(db, user_id, name)`**

- 统计未吊销 Key 数 ≥ 3 → `ValueError("最多 3 个 MCP Key")`
- `raw = _generate_raw_key()`；`key_prefix = raw[:24]`
- 存 `key_hash=_hash_key(raw)`；返回 `{ id, key: raw, keyPrefix, name, claudeConfig, createdAt }`

- [ ] **Step 3: 实现 `list_keys` / `revoke_key`**

- `list_keys`：过滤 `revoked_at IS NULL`，不返回 hash
- `revoke_key`：校验 `user_id` 归属，设 `revoked_at=now()`

- [ ] **Step 4: 实现 `resolve_user_by_key(db, raw_key) -> str | None`**

- 格式须以 `KEY_PREFIX` 开头，否则 `None`
- `computed = _hash_key(raw_key)` → `SELECT ... WHERE key_hash = computed AND revoked_at IS NULL`
- 命中则返回 `user_id`；**不要**全表扫描再 `compare_digest`（hash 已唯一索引）

- [ ] **Step 5: 实现 `touch_last_used(db, key_hash)`**（供 MCP 中间件 `create_task` 异步调用；内部独立 `async_session`）

- [ ] **Step 6: Service 返回字段用 camelCase**（与 `my_words` 一致：`keyPrefix`, `lastUsedAt`, `claudeConfig`）

- [ ] **Step 7: `id` 用 `nanoid.generate()`**（与项目其他模型一致）

- [ ] **Step 8: Commit** `feat(api): add mcp_api_key service`

---

### Task A.3: 主 API Router + 配置

**Files:**
- Create: `server/app/schemas/mcp_keys.py`, `server/app/routers/mcp_keys.py`
- Modify: `server/app/config.py`, `server/app/main.py`, `server/.env.example`

- [ ] **Step 1: `app/config.py` 增加**

```python
mcp_public_url: str = Field(default="http://127.0.0.1:3002/mcp", alias="MCP_PUBLIC_URL")
```

- [ ] **Step 2: Schemas**

```python
# app/schemas/mcp_keys.py
from pydantic import BaseModel, Field

class CreateMcpKeyDto(BaseModel):
    name: str = Field(default="", max_length=64)
```

- [ ] **Step 3: Router `/api/v1/user/mcp-keys`**

挂 `get_current_user` + `get_db`；**JWT 取 `user["userId"]`**（camelCase，与全项目一致）：

| 方法 | 行为 |
|------|------|
| GET | `list_keys` |
| POST | `create_key(..., settings.mcp_public_url)` → `{ data: { key, claudeConfig, ... }, code: 200 }` |
| DELETE `/{key_id}` | `revoke_key` → 404 若不存在 |

- [ ] **Step 4: `app/main.py` 注册 router**

```python
from app.routers import mcp_keys
app.include_router(mcp_keys.router)
```

- [ ] **Step 5: `.env.example` 增加 `MCP_PUBLIC_URL=https://english.example.com/mcp`**

- [ ] **Step 6: Commit** `feat(api): add user mcp-keys CRUD endpoints`

---

### Task A.4: API 冒烟

**Files:**
- Create: `server/scripts/smoke_mcp_keys_api.py`

- [ ] **Step 1: 脚本流程**

1. 用测试用户 JWT（读 `.env` 或硬编码 demo 用户 login API 获取 token）
2. POST 创建 Key → 断言返回 `key` 以 `en_mcp_live_` 开头、`claudeConfig.mcpServers.english.headers`
3. GET 列表 → 含该 prefix
4. `resolve_user_by_key` 直接调 service 断言 user_id 正确
5. DELETE 吊销 → 再 resolve 返回 None

```powershell
cd server
uv run python scripts/smoke_mcp_keys_api.py
```

Expected: 打印 `OK`

- [ ] **Step 2: Commit** `test: add smoke script for mcp-keys API`

---

# Phase B — MCP HTTP 鉴权

### Task B.1: Context + Runtime 模式检测

**Files:**
- Create: `server/english_mcp/context.py`, `server/english_mcp/runtime.py`
- Modify: `server/english_mcp/http_server.py`, `server/english_mcp/__main__.py`

- [ ] **Step 1: `context.py`**

```python
from contextvars import ContextVar
from dataclasses import dataclass

@dataclass(frozen=True)
class AuthenticatedMcpUser:
    user_id: str
    key_prefix: str
    key_hash: str

_mcp_user: ContextVar[AuthenticatedMcpUser | None] = ContextVar("mcp_user", default=None)
_invalid_key_header: ContextVar[bool] = ContextVar("invalid_key_header", default=False)

def get_mcp_user() -> AuthenticatedMcpUser | None:
    return _mcp_user.get()

def set_mcp_user(user: AuthenticatedMcpUser | None) -> None:
    _mcp_user.set(user)

def had_invalid_key_header() -> bool:
    return _invalid_key_header.get()

def set_invalid_key_header(value: bool) -> None:
    _invalid_key_header.set(value)
```

- [ ] **Step 2: `runtime.py`**

```python
import os

def is_http_mode() -> bool:
    return os.environ.get("ENGLISH_MCP_HTTP", "").strip() == "1"
```

- [ ] **Step 3: `http_server.py` 入口设 `os.environ["ENGLISH_MCP_HTTP"] = "1"`**（在 import auth 前）

- [ ] **Step 4: Commit** `feat(mcp): add request context for HTTP auth`

---

### Task B.2: Starlette 中间件

**Files:**
- Create: `server/english_mcp/middleware.py`
- Modify: `server/english_mcp/http_server.py`, `server/english_mcp/server.py`

- [ ] **Step 1: 实现 `McpApiKeyMiddleware`（纯 ASGI，须转发 lifespan）**

```python
HEADER = b"english-mcp-api-key"  # scope["headers"] 为 lower-case bytes

class McpApiKeyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)  # 必须转发，否则 session_manager / MCP 起不来
            return
        if scope["type"] == "http":
            set_mcp_user(None)
            set_invalid_key_header(False)
            raw = _extract_header(scope, HEADER)
            if raw:
                auth = await _resolve_in_session(raw)  # -> AuthenticatedMcpUser | None
                if auth:
                    set_mcp_user(auth)
                    asyncio.create_task(touch_last_used_async(auth.key_hash))
                else:
                    set_invalid_key_header(True)
        await self.app(scope, receive, send)
```

- `_extract_client_ip(scope)`：优先 `x-forwarded-for` 首段，否则 `scope["client"][0]`；写入 ContextVar 供匿名 grammar 限流
- `_resolve_in_session` 调 `mcp_db.async_session` + `resolve_user_by_key`

- [ ] **Step 2: 重写 `http_server.py` 启动**

```python
os.environ["ENGLISH_MCP_HTTP"] = "1"  # 必须在 import auth 之前
from english_mcp.server import mcp
from english_mcp.middleware import McpApiKeyMiddleware

inner = mcp.streamable_http_app()  # 内含 lifespan → session_manager.run()
app = McpApiKeyMiddleware(inner)
uvicorn.run(app, host=mcp_settings.mcp_http_host, port=mcp_settings.mcp_http_port)
```

**勿**在 middleware 外再包一层丢失 lifespan 的 wrapper。若仍有问题，fallback：`http_server` 启动时显式 `mcp_db.init_db()` + shutdown `dispose_db()`。

- [ ] **Step 3: `server.py` FastMCP 构造增加 `stateless_http=True`**

- 生产 `MCP_HTTP_HOST=0.0.0.0` 时配置 `transport_security` allowed_hosts（见 Task D.3）

- [ ] **Step 4: Commit** `feat(mcp): add ENGLISH-MCP-API-KEY middleware for HTTP`

---

### Task B.3: auth.py + tools_handlers 改造

**Files:**
- Modify: `server/english_mcp/auth.py`, `server/english_mcp/tools_handlers.py`, `server/english_mcp/rate_limit.py`, `server/english_mcp/config.py`

- [ ] **Step 1: 重写 `resolve_progress_user_id`**

```python
def resolve_progress_user_id() -> tuple[str | None, str | None]:
    if is_http_mode():
        user = get_mcp_user()
        if user:
            return user.user_id, None
        if had_invalid_key_header():
            return None, "ENGLISH-MCP-API-KEY 无效或已吊销"
        return None, "需要 ENGLISH-MCP-API-KEY，请在平台设置页生成"
    # stdio 回退（现有逻辑）
    ...
```

- [ ] **Step 2: `rate_limit_key()` HTTP 模式用 `key_prefix` 或 client IP**

- 中间件把 `client` IP 写入 ContextVar（可选 `AuthenticatedMcpUser` 扩展）供匿名 grammar 限流

- [ ] **Step 3: `rate_limit.py` 增加 `allow_grammar_anonymous(ip)` — 3/min/IP**

- [ ] **Step 4: `config.py` 增加 `mcp_grammar_require_key: bool = Field(default=False, alias="MCP_GRAMMAR_REQUIRE_KEY")`**

- `run_check_grammar`：HTTP + require_key + 无 user → 返回需 Key 提示

- [ ] **Step 5: Commit** `feat(mcp): enforce per-user auth on HTTP personalized tools`

---

### Task B.4: 端到端冒烟

**Files:**
- Create: `server/scripts/smoke_mcp_keys.py`

- [ ] **Step 1: 脚本分两层**

**层 1（必选，不启 HTTP）**：JWT login → API CRUD；对 handler 测试：

```python
set_mcp_user(AuthenticatedMcpUser(user_id=..., key_prefix=..., key_hash=...))
assert "error" not in json.loads(await run_get_learning_progress())
set_mcp_user(None); os.environ["ENGLISH_MCP_HTTP"] = "1"
assert "error" in json.loads(await run_get_learning_progress())  # HTTP 模式无 Key
```

**层 2（可选）**：subprocess 启 `http_server` + `httpx` POST `/mcp` 带 Header（Streamable HTTP 需 `Accept: application/json, text/event-stream`）

- [ ] **Step 2: Commit** `test: add end-to-end smoke for MCP API key auth`

---

# Phase C — Web 设置页

### Task C.1: 共享类型 + API 模块

**Files:**
- Create: `packages/common/mcp/index.ts`, `apps/web/src/apis/mcp-keys/index.ts`

- [ ] **Step 1: 类型**（导入路径 `@en/common/mcp`，与 `@en/common/word` 同模式；**无** `packages/common/index.ts`）

```typescript
export interface McpApiKeyItem {
  id: string
  name: string
  keyPrefix: string
  createdAt: string
  lastUsedAt: string | null
}

export interface CreateMcpKeyResult {
  id: string
  key: string
  keyPrefix: string
  name: string
  claudeConfig: Record<string, unknown>
  createdAt: string
}
```

- [ ] **Step 2: API 封装** `listMcpKeys`, `createMcpKey`, `revokeMcpKey` → `serverApi`

- [ ] **Step 3: Commit** `feat(web): add mcp-keys API client and types`

---

### Task C.2: 设置页 UI

**Files:**
- Modify: `apps/web/src/views/Setting/index.vue`

- [ ] **Step 1: 新增 el-card「MCP 连接」**

- 说明文案 + 「生成新 Key」按钮
- 表格：前缀、备注、创建时间、最后使用、吊销
- 空态提示

- [ ] **Step 2: 生成流程**

- 弹窗输入备注 → POST
- 成功模态：**完整 Key 只显示一次** + 「复制 Key」+ 「复制 Claude 配置」（`JSON.stringify(claudeConfig, null, 2)`）

- [ ] **Step 3: 吊销确认** `ElMessageBox.confirm`

- [ ] **Step 4: 手动验收** 登录 → 设置 → 生成 → 复制配置

- [ ] **Step 5: Commit** `feat(web): MCP key management on settings page`

---

# Phase D — 部署与文档

### Task D.1: Nginx + 环境变量文档

**Files:**
- Modify: `docs/deploy/nginx.example.conf`, `server/.env.example`
- Create: `docs/mcp-claude-setup.md`

- [ ] **Step 1: nginx 增加 upstream + location `/mcp`**

```nginx
upstream english_mcp {
    server 127.0.0.1:3002;
}
location /mcp {
    proxy_pass http://english_mcp/mcp;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_read_timeout 300s;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

- [ ] **Step 2: 编写 `docs/mcp-claude-setup.md`**

- 用户在设置页生成 Key
- `~/.claude.json` HTTP 配置示例（LangSmith 风格 Header）
- 公开 tool vs 需 Key tool 列表
- 本地开发：stdio vs HTTP

- [ ] **Step 3: `.env.example` 标注 `ENGLISH_MCP_*` 为「仅 stdio 本地开发」；补充 `MCP_GRAMMAR_REQUIRE_KEY`**

- [ ] **Step 4: Commit** `docs: add MCP Claude setup guide and nginx /mcp proxy`

---

### Task D.2: HTTP 配置示例

**Files:**
- Modify: `.mcp.json.example`

- [ ] **Step 1: 文件顶部注释说明两种模式**

- stdio（开发者本地）
- HTTP（生产用户，Key 来自设置页）

- [ ] **Step 2: 增加 HTTP 示例块（占位 URL，不含真实 Key）**

- [ ] **Step 3: Commit** `docs: extend mcp.json.example with HTTP transport`

---

### Task D.3: 生产 FastMCP 安全参数

**Files:**
- Modify: `server/english_mcp/server.py`, `server/.env.example`

- [ ] **Step 1: 当 `MCP_HTTP_HOST=0.0.0.0` 时设置 `transport_security`**

```python
from mcp.server.transport_security import TransportSecuritySettings

transport_security = None
if mcp_settings.mcp_http_host == "0.0.0.0":
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["*"],  # 由 Nginx 终止 TLS；或填具体域名
        allowed_origins=["*"],
    )
mcp = FastMCP(..., stateless_http=True, transport_security=transport_security)
```

- [ ] **Step 2: `.env.example` 补充 `MCP_HTTP_HOST=0.0.0.0` 生产示例**

- [ ] **Step 3: Commit** `chore(mcp): configure transport security for public HTTP bind`

---

## Plan Self-Review

| Spec 章节 | 对应 Task |
|-----------|-----------|
| §3 数据模型 | A.1 |
| §4 主 API | A.2, A.3 |
| §5 HTTP 鉴权 | B.1–B.3 |
| §5.4 HTTP 禁 demo 回退 | B.3 `is_http_mode()` |
| §6 设置页 | C.1, C.2 |
| §7 部署 | D.1, D.3 |
| §9 冒烟 | A.4, B.4 |
| §7.2 匿名 grammar | B.3 |

### 二次审查（2026-06-30）

| 严重度 | 问题 | 处理 |
|--------|------|------|
| 🔴 高 | ASGI middleware 不转发 `lifespan` → MCP session/DB 不初始化 | B.2 明确要求转发 `lifespan` |
| 🔴 高 | `resolve_user_by_key` 误写为 compare_digest 全表扫描 | A.2 改为 hash 唯一索引直查 |
| 🟡 中 | JWT 字段应为 `user["userId"]` | A.2 Step 6 |
| 🟡 中 | API 响应需 camelCase | A.2 Step 7 |
| 🟡 中 | `@en/common` 无根 index，应用 `@en/common/mcp` | C.1 |
| 🟡 中 | Nginx 后匿名限流需读 `X-Forwarded-For` | B.2 |
| 🟡 中 | 生产 `0.0.0.0` 需 `transport_security` | D.3 新增 |
| 🟢 低 | B.4 冒烟应用 handler + ContextVar，HTTP 集成可选 | B.4 分层 |
| 🟢 低 | `touch_last_used` 需独立 session | A.2 Step 5 |

无 TBD；测试以 smoke 脚本 + 手动 Claude CLI 为主（项目无 pytest）。

---

## 答辩 Demo 脚本（Phase A–C 完成后）

1. Web 设置页 → 生成 Key → 复制 Claude 配置  
2. 另一台/新 profile 的 `~/.claude.json` 粘贴配置（仅 URL + Header）  
3. Claude Code `/mcp` → english connected  
4. `lookup_words` 无 Key 可用（若 grammar 公开）  
5. `get_learning_progress` 有 Key 返回正确用户数据  
6. Web 生词本与 MCP `list_my_words` 一致  

---

## 计划修订记录

| 日期 | 修订 |
|------|------|
| 2026-06-30 | 初稿：Phase A–D，对齐 spec 二次审查 |
| 2026-06-30 | 计划二次审查：lifespan 转发、hash 直查、camelCase、transport_security、冒烟分层 |

---

**Plan complete.** 建议执行顺序：Phase A → B → C → D，每阶段 smoke 通过后再进下一阶段。

**执行方式：**

1. **Subagent-Driven** — 每 Task 派生子 agent，任务间 review  
2. **Inline Execution** — 本会话按 Task 连续实现，阶段 checkpoint  

请选择执行方式，或指定「先从 Phase A 开始」。

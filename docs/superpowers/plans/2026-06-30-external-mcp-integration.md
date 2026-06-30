# 外部 MCP 集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 管理员维护 Fetch / Wikipedia / YouTube 三类 MCP 模板；用户在设置页启用并填 Key；`normal` 聊天动态挂载外部 MCP 工具（方案 B）。

**Architecture:** 主 API 存 `mcp_template` + `user_mcp_connection`；AI 服务 `chat.py` preload 外部 LangChain tools；Docker 内网 HTTP sidecar 提供 MCP 端点；Fetch URL 经 `mcp_url_guard` 白名单 + DNS 校验。

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, LangChain tools, Python `mcp` SDK, Vue 3, React Admin, Docker Compose

**Spec:** `docs/superpowers/specs/2026-06-30-external-mcp-integration-design.md`

---

## 文件总览

| Phase | 新建 | 修改 |
|-------|------|------|
| P0 | `docs/external-mcp-setup.md`, `docker/mcp-gateway/*`（spike 结论）, `server/scripts/test_mcp_url_guard.py` | `deploy/docker-compose.yml`（spike 用 fetch-mcp） |
| P1 | models/services/routers/schemas（见各 Task）, `shared/mcp_crypto.py`, `ai/services/mcp_*.py`, `packages/common/external-mcp/`, web/admin 页面, smoke 脚本 | `chat.py`, `tools/__init__.py`, `prompt.py`, `seed` 数据 |
| P2 | wikipedia sidecar compose | Admin seed、`external-mcp-setup.md` |
| P3 | youtube sidecar（若可行） | 同上 |

**硬门槛：** P0 **五项**验收全部通过后再开始 P1 Task 1.1。

---

# Phase P0 — Sidecar Spike（无业务代码）

### Task P0.1: HTTP 网关方案 spike

**Files:**
- Create: `docs/external-mcp-setup.md`（骨架）
- Create: `docker/mcp-gateway/Dockerfile`, `docker/mcp-gateway/entrypoint.sh`（或选定社区镜像的 compose 片段）

- [ ] **Step 1: 评估三种方案并记录**

在 `docs/external-mcp-setup.md` 建表对比：

| 方案 | 优点 | 缺点 |
|------|------|------|
| 社区 mcp-proxy / supergateway | 快 | 维护不确定 |
| 自研 stdio→HTTP 薄包装（Python + `mcp` SDK） | 可控 | 需维护 |
| 单容器 `mcp-gateway` 多 stdio 子进程 | 省内存 | 复杂 |

- [ ] **Step 2: 实现最小 Fetch sidecar**

推荐自研薄包装（与现有 `english_mcp` 同栈）：

```dockerfile
# docker/mcp-gateway/Dockerfile
FROM python:3.12-slim-bookworm
WORKDIR /app
RUN pip install mcp uvicorn --index-url https://pypi.tuna.tsinghua.edu.cn/simple
COPY docker/mcp-gateway/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

`entrypoint.sh` 启动 `@modelcontextprotocol/server-fetch` 的 stdio 进程并由 HTTP 网关转发（具体命令以 spike 实测为准，写入 `external-mcp-setup.md`）。

- [ ] **Step 3: compose 添加 `fetch-mcp`**

```yaml
# deploy/docker-compose.yml 追加
  fetch-mcp:
    build:
      context: ..
      dockerfile: docker/mcp-gateway/Dockerfile
    environment:
      MCP_SERVER: fetch
    deploy:
      resources:
        limits:
          memory: 256M
```

不映射 `ports` 到 host。

- [ ] **Step 4: 从 `ai` 容器内验证 list_tools（勿在宿主机访问 Docker DNS）**

`fetch-mcp` 是 Compose 内网主机名，**宿主机无法解析**。须在 `ai` 容器同网络内执行：

```powershell
# 仓库根目录
docker compose -f deploy/docker-compose.yml up -d fetch-mcp ai
docker compose -f deploy/docker-compose.yml exec ai uv run python -c "
import asyncio
from ai.services.mcp_client import list_tools
async def main():
    tools = await list_tools('http://fetch-mcp:8080/mcp')
    print([t.get('name') for t in tools])
asyncio.run(main())
"
```

Expected: 打印 tool 名称列表，无异常。

> P0 可先用 spike 脚本 `scripts/spike_mcp_list_tools.py`；P1 Task 1.5 将其正式化为 `mcp_client.py`。

- [ ] **Step 5: 记录选定方案到 `docs/external-mcp-setup.md` §P0-1**

- [ ] **Step 6: 记录 MCP Client 实现结论到 `docs/external-mcp-setup.md` §「MCP Client」**

写明 P1 将采用的调用方式（二选一，勿留空）：

- **A** 官方 `mcp` SDK Streamable HTTP session
- **B** `httpx` 裸 JSON-RPC（`tools/list`、`tools/call`）

附 spike 实测命令与样例响应片段。

- [ ] **Step 7: Commit** `docs(spike): external MCP gateway spike for fetch sidecar`

---

### Task P0.2: ECS 内存评估

**Files:**
- Modify: `docs/external-mcp-setup.md` §P0-3

- [ ] **Step 1: SSH ECS 测当前栈**

```bash
ssh root@101.37.235.230
cd /opt/english-project
docker stats --no-stream
free -h
```

- [ ] **Step 2: 临时起 fetch-mcp 再测峰值**

记录 `ai`、`fetch-mcp` 及各服务 MEM USAGE。

- [ ] **Step 3: 书面结论（三选一）**

写入 `docs/external-mcp-setup.md`：

- **A** 升配 ECS 至 ≥4GB
- **B** 合并单 `mcp-gateway` 容器（P1 compose 按 B 调整）
- **C** 仅 Fetch 一个 sidecar，Wikipedia/YouTube 延后

- [ ] **Step 4: Commit** `docs(spike): ECS memory assessment for external MCP`

---

### Task P0.3: SSRF 校验原型

**Files:**
- Create: `server/ai/services/mcp_url_guard.py`
- Create: `server/scripts/test_mcp_url_guard.py`

- [ ] **Step 1: 实现 URL guard**

```python
# server/ai/services/mcp_url_guard.py
"""Fetch 目标 URL 校验：域名白名单 + DNS 私网拦截。"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

DEFAULT_FETCH_ALLOWLIST = (
    "bbc.com", "bbc.co.uk", "wikipedia.org", "medium.com",
    "nationalgeographic.com", "youtube.com", "youtu.be",
)


def _host_allowed(host: str, allowlist: tuple[str, ...]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == suffix or host.endswith("." + suffix) for suffix in allowlist)


def _ip_is_private(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def _resolve_host_ips(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None)
    return list({info[4][0] for info in infos})


def validate_fetch_url(url: str, allowlist: tuple[str, ...] | None = None) -> None:
    """通过则静默；失败 raise ValueError(中文说明)。"""
    allowlist = allowlist or DEFAULT_FETCH_ALLOWLIST
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("仅支持 http/https 链接")
    host = parsed.hostname
    if not host:
        raise ValueError("无效 URL")
    if not _host_allowed(host, allowlist):
        raise ValueError("该域名不在允许列表")
    for ip in _resolve_host_ips(host):
        if _ip_is_private(ip):
            raise ValueError("目标地址不允许访问")
```

- [ ] **Step 2: 冒烟脚本**

```python
# server/scripts/test_mcp_url_guard.py
from ai.services.mcp_url_guard import validate_fetch_url

def main() -> None:
    validate_fetch_url("https://www.bbc.com/news")
    try:
        validate_fetch_url("http://127.0.0.1/")
        raise AssertionError("should reject loopback")
    except ValueError:
        pass
    try:
        validate_fetch_url("http://169.254.169.254/")
        raise AssertionError("should reject metadata")
    except ValueError:
        pass
    print("OK")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 运行**

```powershell
cd server
uv run python scripts/test_mcp_url_guard.py
```

Expected: `OK`

- [ ] **Step 4: Commit** `feat(ai): add fetch URL guard prototype (P0 spike)`

---

### Task P0.4: P0 验收签字

**Files:**
- Modify: `docs/external-mcp-setup.md`

- [ ] **Step 1: 在文档末尾填 P0 Checklist**

```markdown
## P0 验收（日期：____）

- [ ] HTTP 网关方案选定并可复现
- [ ] 从 **ai 容器内** fetch-mcp `list_tools` + `call_tool`（example.com 或 sidecar 支持的测试 URL）成功
- [ ] ECS 内存决策：A / B / C
- [ ] test_mcp_url_guard.py 通过
- [ ] **MCP Client 实现方式**已写入 `docs/external-mcp-setup.md` §「MCP Client」（SDK 或 httpx JSON-RPC）
```

五项全部勾选后再进入 P1。

- [ ] **Step 2: Commit** `docs: complete P0 external MCP spike checklist`

---

# Phase P1 — 框架 + Fetch 端到端

### Task 1.1: ORM + 迁移 + Seed

**Files:**
- Create: `server/app/models/mcp_template.py`, `server/app/models/user_mcp_connection.py`
- Modify: `server/app/models/__init__.py`, `server/alembic/env.py`
- Create: `server/alembic/versions/<rev>_add_external_mcp_tables.py`
- Create: `server/scripts/seed_mcp_templates.py`

- [ ] **Step 1: 创建 `McpTemplate` 模型**

```python
# server/app/models/mcp_template.py
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class McpTemplate(Base):
    __tablename__ = "mcp_template"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    alias: Mapped[str] = mapped_column(String(32), unique=True)
    display_name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(512))
    header_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    globally_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled_roles: Mapped[list] = mapped_column(JSONB, default=list)
    tools_cache: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    exposed_tools: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    fetch_url_allowlist: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 2: 创建 `UserMcpConnection` 模型**

```python
# server/app/models/user_mcp_connection.py
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class UserMcpConnection(Base):
    __tablename__ = "user_mcp_connection"
    __table_args__ = (UniqueConstraint("user_id", "template_id"),)

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(30), ForeignKey("user.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[str] = mapped_column(String(30), ForeignKey("mcp_template.id", ondelete="CASCADE"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    headers_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools_cache: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 3: 迁移 + seed**

```powershell
cd server
uv run alembic revision --autogenerate -m "add external mcp template and connection tables"
uv run alembic upgrade head
uv run python scripts/seed_mcp_templates.py
```

`seed_mcp_templates.py` 插入 fetch/wikipedia/youtube 三条；fetch 带默认 `fetch_url_allowlist`；`globally_enabled=false`。

- [ ] **Step 4: Commit** `feat(db): add mcp_template and user_mcp_connection tables`

---

### Task 1.2: Header 加解密

**Files:**
- Create: `server/shared/mcp_crypto.py`

- [ ] **Step 1: Fernet 封装**

```python
# server/shared/mcp_crypto.py
import base64
import hashlib
import json

from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_headers(headers: dict[str, str]) -> str:
    return _fernet().encrypt(json.dumps(headers).encode()).decode()


def decrypt_headers(token: str) -> dict[str, str]:
    raw = _fernet().decrypt(token.encode())
    data = json.loads(raw.decode())
    if not isinstance(data, dict):
        raise ValueError("invalid headers payload")
    return {str(k): str(v) for k, v in data.items()}
```

- [ ] **Step 2: 在 `scripts/test_mcp_url_guard.py` 同目录加快速验证**

```powershell
cd server
uv run python -c "from shared.mcp_crypto import encrypt_headers, decrypt_headers; h={'Authorization':'x'}; assert decrypt_headers(encrypt_headers(h))==h; print('OK')"
```

- [ ] **Step 3: Commit** `feat(shared): add Fernet helpers for MCP user headers`

---

### Task 1.3: mcp_template Service + Admin API

**Files:**
- Create: `server/app/schemas/mcp_templates.py`
- Create: `server/app/services/mcp_template.py`
- Create: `server/app/routers/admin/mcp_templates.py`
- Modify: `server/app/routers/admin/__init__.py`

- [ ] **Step 1: Schema**

```python
# server/app/schemas/mcp_templates.py
from pydantic import BaseModel, Field

class UpdateMcpTemplateDto(BaseModel):
    url: str | None = None
    description: str | None = None
    globally_enabled: bool | None = None
    header_schema: dict | None = None
    exposed_tools: list[str] | None = None
    fetch_url_allowlist: list[str] | None = None

ALLOWED_MCP_HOSTS = ("fetch-mcp", "wikipedia-mcp", "youtube-mcp", "mcp-gateway", "localhost", "127.0.0.1")
```

- [ ] **Step 2: Service 核心方法**

`list_templates`, `get_template`, `update_template`（校验 url host ∈ ALLOWED_MCP_HOSTS）, `test_template_connection`（调 MCP client list_tools → 写 tools_cache + last_synced_at）。

`resolve_exposed_tools(template)`：若 `exposed_tools` 非空用其；否则从 `tools_cache` 按 name 排序取前 3 个。

- [ ] **Step 3: Admin Router**

前缀 `/mcp-templates`；GET list/detail、PUT update、POST `/{id}/test`；全部 `Depends(get_current_admin)`。

- [ ] **Step 4: 注册 router**

```python
# app/routers/admin/__init__.py
from . import ..., mcp_templates
router.include_router(mcp_templates.router)
```

- [ ] **Step 5: Commit** `feat(admin): MCP template management API`

---

### Task 1.4: user_mcp_connection Service + User API

**Files:**
- Create: `server/app/schemas/external_mcp.py`
- Create: `server/app/services/user_mcp_connection.py`
- Create: `server/app/routers/external_mcp.py`
- Modify: `server/app/main.py`

- [ ] **Step 1: User Service**

`list_available_for_user(user_id)` → globally_enabled 模板 + connection 状态（secret 显示 `configured: true`）。

`upsert_connection(user_id, alias, enabled, headers)` → 加密 headers；若模板未 globally_enabled 则 400。

`test_user_connection(user_id, alias)` → list_tools 写 user tools_cache。

`delete_connection(user_id, alias)` → enabled=false, 清 headers_enc/tools_cache。

- [ ] **Step 2: Router** `/api/v1/user/external-mcp`

- [ ] **Step 3: main.py include_router**

- [ ] **Step 4: Commit** `feat(api): user external MCP connection API`

---

### Task 1.5: MCP HTTP Client

**Files:**
- Create: `server/ai/services/mcp_client.py`
- Create: `server/ai/services/mcp_tool_cache.py`

- [ ] **Step 1: HTTP Client（Streamable HTTP）**

```python
# server/ai/services/mcp_client.py
"""MCP HTTP Client — list_tools / call_tool。"""
from __future__ import annotations

import json
from typing import Any

import httpx

MCP_TIMEOUT = 30.0


async def list_tools(url: str, headers: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """调用 MCP list_tools，返回 tool dict 列表（name, description, inputSchema）。"""
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        resp = await client.post(
            url,
            headers={"Content-Type": "application/json", **(headers or {})},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", {}).get("tools", [])


async def call_tool(
    url: str,
    name: str,
    arguments: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> Any:
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        resp = await client.post(
            url,
            headers={"Content-Type": "application/json", **(headers or {})},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("result")
```

> **注意：** 实现方式 **必须遵循** P0.4 checklist 第 5 项写入 `docs/external-mcp-setup.md` 的结论（SDK 或 httpx JSON-RPC）。下例为 httpx 方案；若 P0 选 SDK，替换实现但保持 `list_tools` / `call_tool` 函数签名不变。

- [ ] **Step 2: 进程内 TTL 缓存（带过期清理，防内存泄漏）**

```python
# server/ai/services/mcp_tool_cache.py
import time
from typing import Any

_TTL = 300
_MAX_ENTRIES = 512
_store: dict[tuple, tuple[float, Any]] = {}


def _cleanup_expired() -> None:
    now = time.time()
    expired = [k for k, (exp, _) in _store.items() if exp <= now]
    for k in expired:
        _store.pop(k, None)


def get_cached(key: tuple) -> Any | None:
    item = _store.get(key)
    if not item:
        return None
    expires, value = item
    if time.time() > expires:
        _store.pop(key, None)
        return None
    return value


def set_cached(key: tuple, value: Any) -> None:
    _cleanup_expired()
    if len(_store) >= _MAX_ENTRIES:
        # 仍满则丢弃最旧条目（按 expires 最早）
        oldest = min(_store.items(), key=lambda kv: kv[1][0])[0]
        _store.pop(oldest, None)
    _store[key] = (time.time() + _TTL, value)
```

- [ ] **Step 3: 验证缓存清理**

```powershell
cd server
uv run python -c "
from ai.services.mcp_tool_cache import set_cached, get_cached, _store, _cleanup_expired
for i in range(600):
    set_cached((i,), i)
assert len(_store) <= 512
print('OK', len(_store))
"
```

Expected: `OK` 且 `_store` 长度 ≤ 512。

- [ ] **Step 4: Commit** `feat(ai): MCP HTTP client and tool list cache`

---

### Task 1.6: external_mcp LangChain 工具 + chat 集成

**Files:**
- Create: `server/ai/services/tools/external_mcp.py`
- Modify: `server/ai/services/tools/__init__.py`
- Modify: `server/ai/services/chat.py`
- Modify: `server/ai/services/prompt.py`（normal 本地 prompt 追加 §5.5 段落）

- [ ] **Step 1: `load_external_mcp_tools(user_id)`**

逻辑见 spec §5.2–§5.6：

- JOIN 查询 enabled 连接
- 取 tools_cache（模板级或用户级）
- `resolve_exposed_tools` 过滤
- 包装 `StructuredTool`，名 `{alias}__{tool_name}`
- Fetch 类 tool：arguments 含 `url` 时先 `validate_fetch_url(url, template.fetch_url_allowlist)`

- [ ] **Step 2: 扩展 make_tools / make_tools_by_role**

新增可选参数 `external_tools: list | None = None`（默认 `None`，**向后兼容**）。`make_tools_by_role` 将参数透传给 `make_tools`。

```python
def make_tools(..., external_tools: list | None = None) -> list:
    ...
    if external_tools:
        tools.extend(external_tools)
    return tools

def make_tools_by_role(..., external_tools: list | None = None) -> list:
    if role == "normal":
        return make_tools(..., external_tools=external_tools)
    ...
```

- [ ] **Step 3: 回归验证现有调用方（签名变更后行为不变）**

代码库内仅 **2 处** 调用 `make_tools_by_role`：`chat.py`（P1 会传 `external_tools`）、`agent_eval.py`（不传，须与改前一致）。

```powershell
cd server
uv run python -c "
from ai.services.tools import make_tools_by_role
n = make_tools_by_role('test-user', 'normal', 'conv-1')
m = make_tools_by_role('test-user', 'master', 'conv-1')
o = make_tools_by_role('test-user', 'oral', 'conv-1')
print('normal', len(n), [t.name for t in n])
print('master', len(m))
print('oral', len(o), [t.name for t in o])
assert len(m) == 0
assert len(o) == 1
"
```

Expected: `normal` 工具数与改前相同（约 5–7，视 web_mode 而定）；`master` 为空；`oral` 仅 1 个 grammar 工具。**未启用 external MCP 时**工具名列表不含 `fetch__` 前缀。

- [ ] **Step 4: chat.py preload**

```python
external_tools: list = []
if role == "normal" and user_id:
    external_tools = await load_external_mcp_tools(user_id)
tools = make_tools_by_role(..., external_tools=external_tools)
```

- [ ] **Step 5: normal prompt 追加外部 MCP 说明**（`prompt.py` 或 Hub 不可用时的 fallback）

- [ ] **Step 6: 手动冒烟**

启用 fetch 模板 + 用户 connection → normal 聊天贴 `https://www.bbc.com/...` → 日志可见 `fetch__` tool call。

- [ ] **Step 7: Commit** `feat(ai): mount external MCP tools in normal chat`

---

### Task 1.7: 集成冒烟脚本

**Files:**
- Create: `server/scripts/smoke_external_mcp_api.py`

- [ ] **Step 1: 脚本流程**

1. Admin 用户 login（或 DB 取 admin）
2. GET `/api/v1/admin/mcp-templates`
3. PUT fetch 模板 `globally_enabled=true`
4. POST test → 断言 tools_cache 非空
5. 普通用户 PUT `/api/v1/user/external-mcp/fetch` `{enabled:true}`
6. POST test → 断言 user tools_cache 或模板 cache 可用

- [ ] **Step 2: 运行**

```powershell
cd server
uv run python scripts/smoke_external_mcp_api.py
```

Expected: `OK`

- [ ] **Step 3: Commit** `chore: add smoke script for external MCP API`

---

### Task 1.8: Web 设置页 — 外部 MCP

**Files:**
- Create: `packages/common/external-mcp/index.ts`
- Create: `apps/web/src/apis/external-mcp/index.ts`
- Modify: `apps/web/src/views/Setting/index.vue`

- [ ] **Step 1: 类型**

```typescript
// packages/common/external-mcp/index.ts
export interface ExternalMcpTemplateItem {
  alias: string;
  displayName: string;
  description: string;
  globallyEnabled: boolean;
  headerSchema: { fields: Array<{ key: string; label: string; required: boolean; secret: boolean; placeholder?: string }> };
  exposedToolNames: string[];
  connection?: {
    enabled: boolean;
    configuredHeaders: Record<string, boolean>;
    lastTestedAt: string | null;
    toolNames: string[];
  };
}
```

- [ ] **Step 2: API client**

`listExternalMcp`, `upsertExternalMcp(alias, body)`, `testExternalMcp(alias)`, `deleteExternalMcp(alias)`。

- [ ] **Step 3: Setting 页新增「外部 MCP」卡片**

每个模板：开关、动态 header 表单、保存/测试按钮、工具列表只读；`globally_enabled=false` 时 disabled + 提示「管理员未开放」。

- [ ] **Step 4: Commit** `feat(web): external MCP settings UI`

---

### Task 1.9: Admin MCP 模板页

**Files:**
- Create: `apps/admin/src/views/mcp-templates/List.tsx`
- Modify: `apps/admin/src/router/index.tsx`, `apps/admin/src/apis/admin.ts`

- [ ] **Step 1: 列表 + 编辑 Drawer**

字段：url、description、globally_enabled、fetch_url_allowlist（仅 fetch）、测试连接按钮、exposed_tools 多选（测试后加载）。

- [ ] **Step 2: 路由 `/mcp-templates` + 侧栏菜单项**

- [ ] **Step 3: Commit** `feat(admin): MCP templates management page`

---

### Task 1.10: Compose 生产化 + 文档

**Files:**
- Modify: `deploy/docker-compose.yml`, `deploy/env.production.example`
- Modify: `docs/external-mcp-setup.md`, `AGENTS.md`（一句）

- [ ] **Step 1: 按 P0 内存决策调整 compose**

- P0 结论 A：三 sidecar 或 gateway + ai depends_on
- P0 结论 B：单 `mcp-gateway` 服务
- P0 结论 C：仅 `fetch-mcp`

- [ ] **Step 2: 文档补充运维步骤**

Admin 开模板 → 用户设置页启用 → 聊天验证。

- [ ] **Step 3: Commit** `docs(deploy): external MCP production setup`

---

# Phase P2 — Wikipedia

### Task 2.1: wikipedia-mcp sidecar

**Files:**
- Modify: `deploy/docker-compose.yml`, `docker/mcp-gateway/*`
- Modify: `server/scripts/seed_mcp_templates.py`（确认 wikipedia URL）

- [ ] **Step 1: 添加 wikipedia sidecar（或 gateway 第二进程）**

- [ ] **Step 2: Admin test wikipedia 模板 → tools_cache 有数据**

- [ ] **Step 3: 用户启用 + normal 聊天「用英文介绍 Shakespeare」冒烟**

- [ ] **Step 4: Commit** `feat(deploy): add wikipedia MCP sidecar`

---

# Phase P3 — YouTube（条件执行）

### Task 3.1: YouTube MCP 调研

- [ ] **Step 1: 在 `docs/external-mcp-setup.md` 记录候选实现与 HTTP 可行性**

- [ ] **Step 2: 若不可行** — youtube 模板保持 `globally_enabled=false`，文档说明阻塞原因，**结束 P3**

### Task 3.2: YouTube sidecar（仅当 3.1 可行）

- [ ] **Step 1: compose + seed + Admin test**

- [ ] **Step 2: 用户贴 YouTube 链接聊天冒烟**

- [ ] **Step 3: Commit** `feat(deploy): add youtube transcript MCP sidecar`

---

## Spec 覆盖自检

| Spec 章节 | Plan Task |
|-----------|-----------|
| §3 数据模型 | 1.1 |
| §4 Admin/User API | 1.3, 1.4 |
| §5 AI 集成 | 1.5, 1.6 |
| §5.6 exposed_tools | 1.3 resolve_exposed_tools, 1.9 Admin UI |
| §6 P0 spike | P0.1–P0.4 |
| §6 sidecar | P0.1, 1.10, P2, P3 |
| §7 前端 | 1.8, 1.9 |
| §8 SSRF | P0.3, 1.6 fetch validate |
| §10 测试 | P0.3, 1.5 Step 3, 1.6 Step 3, 1.7 |

---

## 修订记录

| 日期 | 变更 |
|------|------|
| 2026-06-30 | 初稿 |
| 2026-06-30 | mimo review：P0 改 ai 容器内验证；P0 五项含 MCP Client 结论；TTL 缓存 MAX_ENTRIES + cleanup；Task 1.6 增加 make_tools 调用方回归 |

---

## 执行选项

**Plan 已保存至** `docs/superpowers/plans/2026-06-30-external-mcp-integration.md`。

审查通过后可选：

1. **Subagent-Driven（推荐）** — 每 Task 派生子 agent，Task 间人工 review
2. **Inline Execution** — 本会话按 Phase 顺序执行，Phase 边界 checkpoint 审查

请告知审查意见或直接选择执行方式。

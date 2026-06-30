# English MCP 用户 API Key 与中心化 HTTP 接入设计

**日期**: 2026-06-30  
**状态**: 待用户审阅  
**范围**: 用户在 Web 设置页生成 MCP API Key；任意用户通过 Claude Code HTTP MCP 连接托管服务（方案 1）  
**前置**: [2026-06-29-english-mcp-vocabulary-design.md](./2026-06-29-english-mcp-vocabulary-design.md)（Phase 0–3 已实现）

---

## 1. 背景与目标

### 1.1 现状问题

| 问题 | 说明 |
|------|------|
| Key 写死在 `server/.env` | `ENGLISH_MCP_API_KEY` + `ENGLISH_MCP_USER_ID` 或 `ENGLISH_MCP_DEMO_USER_ID`，全进程共用一个身份 |
| stdio 项目级配置 | 队友必须 clone 仓库、配 `.env`、在项目目录打开 Claude Code |
| 与 LangSmith 体验不一致 | LangSmith：官网领 Key → 在 `~/.claude.json` 配 URL + Header；English MCP 尚未支持 |

### 1.2 目标（用户确认）

1. **中心化托管 HTTP MCP**（方案 1）：部署公网 `https://域名/mcp`，用户**无需** clone 仓库
2. **Web 设置页生成 Key**：登录用户在「设置」中创建/查看/吊销 MCP Key
3. **Claude 配置对齐 LangSmith**：使用 `headers.ENGLISH-MCP-API-KEY`，非 Bearer（与 LangSmith `LANGSMITH-API-KEY` 同模式）
4. **一 Key 一用户**：Key 绑定登录用户，用于进度、生词本、推荐等个性化 tool

### 1.3 非目标（本阶段不做）

- OAuth 2.0 / MCP 官方 Authorization Server 全套流程
- Admin 后台代用户发 Key（用户自助即可）
- 按 Key 计费、配额套餐
- 废弃 stdio 本地 MCP（保留给开发者）

---

## 2. 架构

```
┌─────────────┐     JWT      ┌──────────────────┐
│ Web 设置页   │ ──────────► │ 主 API :3000      │
│ 生成/吊销 Key│             │ /api/v1/user/     │
└─────────────┘             │   mcp-keys        │
                            └────────┬─────────┘
                                     │ 读写
                                     ▼
                            ┌──────────────────┐
                            │ Postgres          │
                            │ mcp_api_key 表    │
                            └────────┬─────────┘
                                     │ 校验 hash
                                     ▼
┌─────────────┐  ENGLISH-MCP-API-KEY  ┌──────────────────┐
│ Claude Code │ ────────────────────► │ MCP HTTP :3002   │
│ ~/.claude   │  POST /mcp            │ english_mcp      │
│ .json       │                       │ → app/services/  │
└─────────────┘                       └──────────────────┘
```

| 组件 | 职责 |
|------|------|
| **主 API** | Key CRUD（JWT）；返回 Claude 配置片段 |
| **MCP HTTP** | 读 Header → 查 Key → 注入 `user_id` 到请求上下文 |
| **`app/services/`** | 业务逻辑不变，MCP tool handler 从上下文取 `user_id` |

**部署**：Nginx `location /mcp` → `127.0.0.1:3002`；SSE buffering off（与 `/ai` 相同）。

**环境变量（服务端）**：

| 变量 | 用途 |
|------|------|
| `MCP_PUBLIC_URL` | 设置页生成 Claude 配置片段中的 URL（**主 API** `app/config.py`，非 `english_mcp`） |
| `MCP_HTTP_HOST` / `MCP_HTTP_PORT` | MCP 进程监听（生产 `0.0.0.0:3002`） |
| `ENGLISH_MCP_DEMO_USER_ID` | **仅开发/stdio 回退**；生产 HTTP 可不配 |

---

## 3. 数据模型

### 3.1 表 `mcp_api_key`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(30)` PK | nanoid |
| `user_id` | `String(30)` FK → `user.id` | 所属用户 |
| `name` | `String(64)` | 用户备注，如「我的 MacBook」 |
| `key_prefix` | `String(24)` | 展示用前缀，如 `en_mcp_live_7Kx9mN2p`（固定前缀 + 随机段前 8 位） |
| `key_hash` | `String(64)` | SHA-256(完整 key)，不可逆 |
| `created_at` | `DateTime` | 创建时间 |
| `last_used_at` | `DateTime` nullable | 最近一次成功校验 |
| `revoked_at` | `DateTime` nullable | 非空即已吊销 |

**索引**：`key_hash` UNIQUE；`user_id` INDEX。

### 3.2 Key 格式

- 完整 Key：`en_mcp_live_<32 位 url-safe random>`
- 示例：`en_mcp_live_7Kx9mN2pQ8vR4sT6uW1yZ3aB5cD7eF9g`
- **明文仅创建时返回一次**；之后列表只显示 `key_prefix + ••••`

### 3.3 约束

- 每用户最多 **3 个**未吊销 Key
- 吊销后不可恢复，需新建

---

## 4. 主 API（Web 后端）

**Router 前缀**：`/api/v1/user/mcp-keys`（挂于现有 user 域，JWT 必须）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `""` | 当前用户 Key 列表（不含明文） |
| `POST` | `""` | 创建 Key；body: `{ "name": "可选备注" }`；响应含 **一次性** `key` + `claudeConfig` |
| `DELETE` | `/{keyId}` | 吊销（软删除：`revoked_at=now()`） |

**Service**：`app/services/mcp_api_key.py`

- `create_key(db, user_id, name) -> { id, key, key_prefix, claude_config, ... }`
- `list_keys(db, user_id) -> list`
- `revoke_key(db, user_id, key_id) -> bool`
- `resolve_user_by_key(db, raw_key) -> user_id | None`（MCP 与主 API 共用）

**`claudeConfig` 响应示例**（服务端拼好，前端一键复制）：

```json
{
  "mcpServers": {
    "english": {
      "type": "http",
      "url": "https://english.example.com/mcp",
      "headers": {
        "ENGLISH-MCP-API-KEY": "en_mcp_live_7Kx9..."
      },
      "timeout": 60000
    }
  }
}
```

`url` 来自 `MCP_PUBLIC_URL` 环境变量。

---

## 5. MCP HTTP 鉴权

### 5.1 Header 约定

与 LangSmith 对齐：

```
ENGLISH-MCP-API-KEY: en_mcp_live_...
```

**不**使用 `Authorization: Bearer` 作为用户-facing 配置（实现层可内部转换）。

### 5.2 请求上下文

- `english_mcp/context.py`：`ContextVar[AuthenticatedMcpUser | None]`
- HTTP 中间件（Starlette）：每个 `/mcp` 请求读取 Header → `resolve_user_by_key` → 写入 ContextVar；更新 `last_used_at`（异步、不阻塞响应）
- **无 Key 或 Key 无效**：ContextVar 为 `None`，**不拒绝连接**（允许 MCP 握手与公开 tool）

### 5.3 Tool 级权限

| Tool | 无 Key | 有效 Key |
|------|--------|----------|
| `lookup_words` | ✅ | ✅ |
| `check_grammar` | ✅（按 IP/Key 限流） | ✅ |
| `list_courses` | ✅ | ✅ |
| `search_knowledge` | ✅ | ✅ |
| `platform_health` | ✅ | ✅ |
| `get_learning_progress` | ❌ 返回 `{ "error": "需要 ENGLISH-MCP-API-KEY，请在平台设置页生成" }` | ✅ |
| `list_my_words` | ❌ | ✅ |
| `add_words_to_review` | ❌ | ✅ |
| `mark_words_mastered` | ❌ | ✅ |
| `recommend_courses` | ❌ | ✅ |
| Resources `english://user/progress` | ❌ | ✅ |
| Resource `english://courses/catalog` | ✅ | ✅ |

### 5.4 `auth.py` 改造

```python
def resolve_progress_user_id() -> tuple[str | None, str | None]:
    # HTTP 模式（english_mcp.http_server）：
    #   仅 ContextVar（Header 校验结果）；禁止 ENGLISH_MCP_DEMO_USER_ID / .env 配对回退
    # stdio 模式（python -m english_mcp）：
    #   1. ENGLISH_MCP_API_KEY + ENGLISH_MCP_USER_ID（.env，本地开发）
    #   2. ENGLISH_MCP_DEMO_USER_ID（demo 回退）
```

**重要**：HTTP 生产路径若仍回退 demo user，则任意人可无 Key 访问个性化 tool，必须禁用。

`rate_limit_key()`：HTTP 模式优先 `key_prefix`（来自 ContextVar）；stdio 用 env Key；否则 `"anonymous"`。

**无效 Key**（Header 有值但校验失败）：ContextVar 为 `None`；私有 tool 返回 `{ "error": "ENGLISH-MCP-API-KEY 无效或已吊销" }`（与「未提供 Key」区分）。

### 5.5 中间件挂载方式

FastMCP 无「自定义 Header 鉴权」插件。实现路径：

1. `http_server.py` 调用 `app = mcp.streamable_http_app()` 取得 Starlette app
2. 外包一层 `Middleware` 读取 `ENGLISH-MCP-API-KEY` → `resolve_user_by_key` → 写入 ContextVar
3. 用 `uvicorn.run(wrapped_app)` 启动（**不**再直接 `mcp.run(transport=...)`，或在其前替换 app）

`last_used_at` 更新：校验成功后 `asyncio.create_task` 异步写库，不阻塞 MCP 响应。

生产建议 `stateless_http=True`（FastMCP 构造参数），便于 Nginx 后多 worker；每请求独立 ContextVar。

### 5.6 与 FastMCP 内置 OAuth 的关系

**不使用** FastMCP `BearerAuthBackend`（仅支持标准 Bearer）。采用 **自定义 Starlette 中间件** 解析 `ENGLISH-MCP-API-KEY`，与 LangSmith Header 名一致。

---

## 6. Web 设置页 UX

**位置**：`apps/web/src/views/Setting/index.vue` 新增卡片 **「MCP 连接」**

| 元素 | 行为 |
|------|------|
| 说明文案 | 「在 Claude Code 中使用 English 平台能力。在 LangSmith 同级位置配置 MCP。」 |
| 「生成新 Key」 | 弹窗输入备注 → POST → **模态框显示完整 Key（仅一次）** + 「复制 Key」+ 「复制 Claude 配置」 |
| Key 列表 | 前缀、备注、创建时间、最后使用、吊销按钮 |
| 链接 | 「查看接入文档」→ spec 或 README 锚点 |

**API 模块**：`apps/web/src/apis/mcp-keys/index.ts`  
**类型**：`packages/common` 增加 `McpApiKey` 相关类型。

---

## 7. 部署与安全

### 7.1 Nginx（片段）

```nginx
location /mcp {
    proxy_pass http://127.0.0.1:3002/mcp;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_read_timeout 300s;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### 7.2 安全

| 项 | 措施 |
|----|------|
| Key 存储 | 仅 hash；明文不落库、不写日志 |
| 传输 | 生产必须 HTTPS |
| 吊销 | 即时生效（查库见 `revoked_at`） |
| 暴力猜测 | Key 空间 ≥ 2^192；`hmac.compare_digest` 比较 hash；失败不写 `last_used_at` |
| 匿名滥用 | `check_grammar` 调 DeepSeek 有成本；匿名限流 **3/min/IP**（严于现有 15/min/Key）；生产可配置 `MCP_GRAMMAR_REQUIRE_KEY=true` 强制要 Key |
| 日志 | 禁止打印完整 Key；可记录 `key_prefix` |
| 多 worker | 语法限流当前为进程内 dict，HTTP 生产需 Redis 或接受 per-worker 限额（与现有 grammar 一致，文档注明） |

### 7.3 进程

生产需常驻：

```bash
uv run python -m uvicorn app.main:socket_app --host 0.0.0.0 --port 3000
uv run python -m uvicorn ai.main:ai_app --host 0.0.0.0 --port 3001
uv run python -m english_mcp.http_server   # 或 systemd 单元 english-mcp.service
```

---

## 8. 迁移与兼容

| 场景 | 行为 |
|------|------|
| 现有 `.env` demo 配置 | stdio 本地开发仍可用 |
| 现有 `.mcp.json.example` | 保留 stdio 示例；新增 `docs/mcp-claude-setup.md` 或 README 章节写 HTTP 示例 |
| 已部署答辩环境 | 配 `MCP_PUBLIC_URL` + 开 HTTP MCP 进程即可 |

**废弃（生产 HTTP 路径）**：不再文档推荐 `ENGLISH_MCP_API_KEY` + `ENGLISH_MCP_USER_ID` 手动配对；`.env.example` 标注为「仅本地 stdio 开发」。

---

## 9. 测试与验收

### 9.1 冒烟脚本

- `server/scripts/smoke_mcp_keys.py`：创建 Key（调主 API + JWT）→ HTTP MCP 带 Header 调 `get_learning_progress` → 吊销 → 再调应失败

### 9.2 手动验收

1. Web 设置页生成 Key，复制 Claude 配置
2. 新机器 `~/.claude.json` 只配 URL + Header，**不 clone 仓库**
3. Claude Code `/mcp` → english connected
4. `lookup_words` 无 Key 可用；`get_learning_progress` 无 Key 报错；有 Key 返回正确用户数据
5. Web 生词本与 MCP `list_my_words` 数据一致

---

## 10. 实现分期建议

| Phase | 内容 |
|-------|------|
| **A** | 迁移 + Model + Service + 主 API CRUD + 冒烟 |
| **B** | MCP HTTP 中间件 + ContextVar + tool 级鉴权 + `smoke_mcp_keys.py` |
| **C** | Web 设置页 UI + 复制配置 |
| **D** | Nginx 示例 + `MCP_PUBLIC_URL` + 文档 |

---

## 11. Spec Self-Review（二次审查 2026-06-30）

| 检查项 | 结果 |
|--------|------|
| TBD / 占位 | 无 |
| 内部矛盾 | 已修：HTTP 模式禁止 demo/env 回退（§5.4） |
| 范围 | 单 spec 可拆 4 Phase |
| 歧义 | 已修：无效 Key vs 未提供 Key 错误文案；`key_prefix` 长度 |

**审查发现（已写入 spec 或 Phase D）：**

| 严重度 | 问题 | 处理 |
|--------|------|------|
| 🔴 高 | HTTP 仍走 `DEMO_USER_ID` 会绕过 Key | §5.4 明确 HTTP 仅 ContextVar |
| 🔴 高 | 匿名 `check_grammar` 可刷 DeepSeek 费用 | §7.2 加强 IP 限流 + 可选强制 Key |
| 🟡 中 | FastMCP 无原生自定义 Header 鉴权 | §5.5 明确 wrap Starlette app |
| 🟡 中 | `key_prefix` 字段 16 字符不够 | 改为 24 |
| 🟡 中 | `MCP_PUBLIC_URL` 应属主 API config | §2 已注明 |
| 🟡 中 | `docs/deploy/nginx.example.conf` 尚无 `/mcp` | Phase D 补 upstream + location |
| 🟢 低 | 语法限流进程内 dict，多 worker 不共享 | §7.2 注明，与现网一致 |
| 🟢 低 | 生产 `0.0.0.0` 需配置 FastMCP `transport_security` | Phase D 部署清单补充 |

**仍接受的风险（本阶段）：**

- Key 校验每请求查库：量级答辩可接受；高 QPS 再加 Redis 缓存 hash→user_id
- 不做 Key 轮换/过期时间（仅手动吊销）

---

## 12. 修订记录

| 日期 | 修订 |
|------|------|
| 2026-06-30 | 初稿：方案 1 + Web 发 Key + `ENGLISH-MCP-API-KEY` Header（对齐 LangSmith） |
| 2026-06-30 | 二次审查：HTTP 禁 demo 回退、中间件挂载、key_prefix 长度、匿名 grammar 限流 |

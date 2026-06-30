# English MCP 用户 API Key 鉴权设计

**日期**: 2026-06-30  
**状态**: 待用户审阅  
**范围**: 中心化 HTTP MCP + Web 设置页签发 Key（LangSmith 式接入）  
**前置**: [2026-06-29-english-mcp-vocabulary-design.md](./2026-06-29-english-mcp-vocabulary-design.md)（Phase 0–3 已实现）

---

## 1. 背景与目标

### 1.1 现状问题

| 项目 | 现状 |
|------|------|
| MCP 鉴权 | `server/.env` 中 `ENGLISH_MCP_API_KEY` + `ENGLISH_MCP_USER_ID` 或 `ENGLISH_MCP_DEMO_USER_ID`，**服务端写死、不查库** |
| 多用户 | 全 MCP 进程共用一个身份，无法在 Claude 侧「每人一把 Key」 |
| 接入方式 | 项目级 stdio + clone 仓库；外部用户无法「只配 URL + Key」 |

### 1.2 目标（用户确认）

- **方案 1**：独立 `english_mcp.http_server` 进程，Nginx 暴露公网 `https://域名/mcp`
- **Web 设置页**：登录用户自助生成 / 查看 / 吊销 MCP Key
- **Claude 配置**：与 LangSmith 一致，在 `headers` 中填写 Key（**不用**顶层 `apiKey` 字段）

```json
{
  "mcpServers": {
    "english": {
      "type": "http",
      "url": "https://english.example.com/mcp",
      "headers": {
        "ENGLISH-MCP-API-KEY": "en_mcp_live_xxxxxxxx"
      },
      "timeout": 60000
    }
  }
}
```

### 1.3 非目标（本阶段不做）

- OAuth / Claude 官方 Connector 市场入驻
- 多 Key 计费、套餐、用量账单
- Admin 代用户发 Key（用户自助即可）
- 替换 stdio 本地开发路径（保留，见 §6）

---

## 2. 架构

```
┌─────────────┐     JWT      ┌──────────────┐     CRUD     ┌─────────────┐
│ Web 设置页   │ ──────────► │ 主 API :3000  │ ──────────► │ mcp_api_key │
└─────────────┘              └──────────────┘              │   (Postgres) │
                                                             └──────▲──────┘
┌─────────────┐  ENGLISH-MCP-API-KEY                           │
│ Claude Code │ ───────────────────────────────────────────────┤
└─────────────┘              ┌──────────────┐                  │
                             │ MCP HTTP :3002│ ── verify hash ──┘
                             │  /mcp         │
                             └──────────────┘
                                      │
                                      ▼
                             app/services/*（与 Web/AI 共用）
```

| 组件 | 职责 |
|------|------|
| `app/models/mcp_api_key.py` | Key 元数据与 hash |
| `app/services/mcp_key.py` | 生成、列表、吊销、校验 |
| `app/routers/user.py` 或子路由 | `GET/POST/DELETE /api/v1/user/mcp-keys` |
| `english_mcp/auth.py` | HTTP：从 Header 解析 Key → `user_id`；stdio 开发回退 |
| `english_mcp/tools_handlers.py` | 个性化 tool 使用 request-scoped `user_id` |
| `apps/web/Setting` | Key 管理 UI + 复制 Claude 配置 |

---

## 3. 数据模型

### 3.1 表 `mcp_api_key`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(30)` PK | nanoid |
| `user_id` | `String(30)` FK → `user.id` | 所属用户 |
| `key_prefix` | `String(16)` | 固定 `en_mcp_live`（便于识别） |
| `key_last4` | `String(4)` | 列表展示用 |
| `key_hash` | `String(64)` | SHA-256(raw_key + pepper)；**不存明文** |
| `label` | `String(64)` nullable | 用户备注，如「MacBook Claude」 |
| `created_at` | `DateTime` | |
| `last_used_at` | `DateTime` nullable | MCP 校验成功时更新 |
| `revoked_at` | `DateTime` nullable | 非空即失效 |

**约束**

- 每用户最多 **5** 条 `revoked_at IS NULL` 的有效 Key
- 索引：`(key_hash)` unique；`(user_id, revoked_at)`

### 3.2 Key 格式

- 明文：`en_mcp_live_` + 32 字符 `[a-zA-Z0-9]`（示例：`en_mcp_live_7Kx9mN2pQ8vR4sT6uW1yZ3aB5cD7eF9g`）
- 创建 API **仅一次**返回完整明文；之后列表只显示 `en_mcp_live_…eF9g`（prefix + last4）

### 3.3 Hash

```text
key_hash = sha256(f"{raw_key}:{settings.secret_key_pepper}").hexdigest()
```

pepper 使用现有 `SECRET_KEY`（或专用 `MCP_KEY_PEPPER`，默认回落 `SECRET_KEY`）。

---

## 4. REST API（主服务 :3000）

前缀：`/api/v1/user/mcp-keys`，均需 JWT（`get_current_user`）。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 列出当前用户 Key（不含 hash/明文） |
| `POST` | `/` | 创建 Key；body 可选 `{ "label": "..." }`；响应含 **一次性** `key` 字段 |
| `DELETE` | `/{key_id}` | 吊销（写 `revoked_at`） |

**响应示例（POST）**

```json
{
  "data": {
    "id": "abc123",
    "label": "MacBook",
    "keyPrefix": "en_mcp_live",
    "keyLast4": "eF9g",
    "key": "en_mcp_live_7Kx9mN2pQ8vR4sT6uW1yZ3aB5cD7eF9g",
    "claudeConfigSnippet": "{ ... 完整 JSON 片段 ... }",
    "createdAt": "2026-06-30T08:00:00Z"
  }
}
```

`claudeConfigSnippet` 由服务端用 `MCP_PUBLIC_BASE_URL` 环境变量拼好，用户一键复制。

**限流**：创建 Key `5/hour/user`；列表/删除 `60/minute/user`。

---

## 5. MCP HTTP 鉴权

### 5.1 Header

| Header | 必填 | 说明 |
|--------|------|------|
| `ENGLISH-MCP-API-KEY` | 个性化 tool 必填 | 与 LangSmith `LANGSMITH-API-KEY` 同模式 |
| `Authorization: Bearer …` | 否 | 本阶段**不采用**（文档与 UI 统一用上一列） |

### 5.2 校验流程

1. Streamable HTTP 请求进入 `english_mcp`
2. `auth.resolve_user_id_from_http(headers)` → 查 `mcp_api_key`（hash 匹配且未吊销）
3. 命中 → 写入 request context（`user_id`）；更新 `last_used_at`（异步、可节流）
4. 未命中 → 个性化 tool 返回 JSON `{"error": "无效或已吊销的 MCP API Key"}`

### 5.3 Tool 权限

| Tool / Resource | 无 Key | 有效 Key |
|-----------------|--------|----------|
| `lookup_words` | ✅ | ✅ |
| `check_grammar` | ✅（按 Key 或 IP 限流） | ✅ |
| `list_courses` | ✅ | ✅ |
| `search_knowledge` | ✅ | ✅ |
| `platform_health` | ✅ | ✅ |
| `english://courses/catalog` | ✅ | ✅ |
| `get_learning_progress` | ❌ | ✅ |
| `recommend_courses` | ❌ | ✅ |
| `list_my_words` | ❌ | ✅ |
| `add_words_to_review` | ❌ | ✅ |
| `mark_words_mastered` | ❌ | ✅ |
| `english://user/progress` | ❌ | ✅ |

公开 tool 便于未登录用户体验；个性化数据必须 Key。

### 5.4 stdio 本地开发（保留）

| 变量 | 用途 |
|------|------|
| `ENGLISH_MCP_DEMO_USER_ID` | 本机 stdio 答辩/demo，**生产 HTTP 不依赖** |
| `ENGLISH_MCP_API_KEY` + `ENGLISH_MCP_USER_ID` | **废弃**，文档标记 deprecated；实现保留只读兼容一个版本 |

HTTP 模式 **禁止** 使用 `.env` 中的 demo user 作为 fallback（避免公网匿名冒充）。

---

## 6. Web 设置页 UX

在 `apps/web/src/views/Setting/index.vue` 新增卡片 **「MCP 连接（Claude Code）」**：

1. **说明**：登录后在 Claude Code 的 `~/.claude.json` 添加 HTTP MCP；Key 仅显示一次。
2. **生成 Key**：按钮 → 弹窗展示明文 +「复制 Key」「复制 Claude 配置」
3. **我的 Key 列表**：label、创建时间、last4、最后使用时间、吊销按钮
4. **文档链接**：指向 spec 或 README 小节

复制内容模板（服务端生成，`url` 来自 `MCP_PUBLIC_BASE_URL`）：

```json
{
  "mcpServers": {
    "english": {
      "type": "http",
      "url": "https://english.example.com/mcp",
      "headers": {
        "ENGLISH-MCP-API-KEY": "<粘贴生成的 Key>"
      },
      "timeout": 60000
    }
  }
}
```

---

## 7. 部署

### 7.1 进程

| 进程 | 端口 | 说明 |
|------|------|------|
| 主 API | 3000 | Key CRUD |
| AI | 3001 | 不变 |
| MCP HTTP | 3002 | `uv run python -m english_mcp.http_server` |

### 7.2 环境变量（新增）

```env
# 设置页复制 Claude 配置用的公网 MCP 地址（含路径 /mcp）
MCP_PUBLIC_BASE_URL=https://english.example.com/mcp

# HTTP 监听（生产建议 127.0.0.1 + Nginx 反代）
MCP_HTTP_HOST=127.0.0.1
MCP_HTTP_PORT=3002
```

### 7.3 Nginx（追加）

```nginx
upstream english_mcp {
    server 127.0.0.1:3002;
}

location /mcp {
    proxy_pass http://english_mcp;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
    proxy_cache off;
    # 必须转发用户 Key
    proxy_set_header ENGLISH-MCP-API-KEY $http_english_mcp_api_key;
}
```

生产必须 **HTTPS**。

### 7.4 安全

- Key 只存 hash；创建后不可再次查看明文
- 吊销立即生效（查库 `revoked_at IS NULL`）
- 每 Key 独立语法检查限流 bucket
- 可选后续：用户改密码时批量吊销 Key（本阶段不做）

---

## 8. 实现阶段建议

| 阶段 | 内容 |
|------|------|
| **A1** | Alembic 迁移 + `mcp_key` service + REST API + smoke |
| **A2** | `english_mcp` HTTP 按 Header 鉴权 + tool 权限矩阵 |
| **A3** | Web 设置页 + 复制 snippet |
| **A4** | Nginx 示例、`.env.example`、`docs` 用户接入说明；废弃 `.env` 双变量文档 |

---

## 9. 验收

1. 用户 A 在设置页生成 Key，用户 B 无法看到
2. Claude Code 仅配 `url` + `ENGLISH-MCP-API-KEY`，**无需 clone 仓库**
3. `get_learning_progress` / `list_my_words` 返回 Key 对应用户数据
4. 吊销 Key 后，Claude 调用个性化 tool 立即失败
5. 无 Key 时 `lookup_words` 仍可用
6. 设置页「复制 Claude 配置」粘贴即可用（仅替换域名若需要）

---

## 10. 修订记录

| 日期 | 修订 |
|------|------|
| 2026-06-30 | 初稿：方案 1 + LangSmith 式 Header + 设置页发 Key |

---

## Spec Self-Review

- [x] 无 TBD / 占位符
- [x] Header 命名与 LangSmith 模式一致（`ENGLISH-MCP-API-KEY`）
- [x] HTTP 生产路径不依赖 demo user；stdio 开发路径单独说明
- [x] 与现有 `app/services/` 复用策略一致
- [x] 范围可拆为 A1–A4 单一实现计划

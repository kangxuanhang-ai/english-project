# 外部 MCP 集成设计（Admin 模板 + 用户设置页启用）

**日期**: 2026-06-30  
**状态**: 已修订（2026-06-30 mimo review）  
**范围**: 管理员维护 Fetch / Wikipedia / YouTube 字幕三类外部 MCP 模板；用户在 Web 设置页启用并填写个人 API Key；`normal` 角色 AI 聊天动态挂载外部 MCP 工具  
**前置**:
- [2026-06-29-english-mcp-vocabulary-design.md](./2026-06-29-english-mcp-vocabulary-design.md)
- [2026-06-30-english-mcp-api-key-auth-design.md](./2026-06-30-english-mcp-api-key-auth-design.md)（已实现 English 对外 MCP）

---

## 1. 背景与目标

### 1.1 现状

| 能力 | 状态 |
|------|------|
| English 平台 **对外** 提供 MCP（Claude Code 连 `english`） | ✅ 已实现 |
| AI 聊天 **内置** LangChain 工具（查词、语法、进度、推荐、知识库、Bocha） | ✅ 已实现 |
| AI 聊天调用 **第三方 MCP** | ❌ 无 |
| 用户/管理员配置外部 MCP | ❌ 无 |

### 1.2 目标（用户确认）

1. **三个外部 MCP 类型**：Fetch（读网页）、Wikipedia（英文百科）、YouTube 字幕（有稳定 HTTP 实现时接入）
2. **方案 B**：管理员维护 MCP **模板**（URL、说明、是否需 Key）；用户在 **设置页** 勾选启用并填写 **个人 Headers/Key**
3. **仅 `normal` 角色** AI 聊天可用外部 MCP 工具（与现有内置工具并存）
4. **学员侧零上传**：贴链接/打字即可，不需要上传图片或视频文件

### 1.3 非目标（本阶段不做）

- 用户任意填写 MCP URL（防 SSRF，URL 仅管理员可改）
- stdio MCP 动态拉起
- 非 `normal` 角色挂载外部 MCP
- 聊天上传图片 / OCR
- OAuth 式 MCP 授权流程
- 按 MCP 调用计费

---

## 2. 架构

```
┌──────────────────┐                    ┌─────────────────────┐
│ Admin 后台        │  维护模板（仅 seed 三条）│ Postgres             │
│ MCP 模板管理      │ ─────────────────► │ mcp_template         │
└──────────────────┘                    │ user_mcp_connection  │
                                        └──────────┬──────────┘
┌──────────────────┐  启用/填 Key                   │
│ Web 设置页        │ ─────────────────────────────►│
│ Tab: 外部 MCP     │                               │
└──────────────────┘                               │
                                                   │
┌──────────────────┐  await load_external_mcp_tools   │
│ AI 服务 :3001     │ ◄──────────────────────────────┘
│ normal 聊天       │
│  ├─ 内置 tools    │  chat.py 内 await 加载后传入 make_tools
│  └─ 外部 MCP tools│─── HTTP MCP Client ───► fetch-mcp (内网)
│     (带 alias 前缀)│─── HTTP MCP Client ───► wikipedia-mcp
│                   │─── HTTP MCP Client ───► youtube-mcp
└──────────────────┘
```

| 组件 | 职责 |
|------|------|
| **主 API :3000** | Admin 模板维护（无 POST 新建）；用户连接 CRUD；加密存储用户 Headers |
| **AI :3001** | 读取用户已启用连接 + 模板 URL；`list_tools` 缓存；包装为 LangChain 工具 |
| **MCP Sidecar 容器** | Docker Compose 内运行 HTTP 版 Fetch/Wikipedia/YouTube MCP（内网） |
| **Web 设置页** | 展示三个模板卡片：开关 + Key 输入 + 测试连接 |
| **Admin** | 编辑模板 URL、全局启用、刷新工具缓存 |

**与现有 English MCP 的关系**：

| 方向 | 设置页 Tab | 协议 |
|------|------------|------|
| Claude Code → English 平台 | 「连接 English MCP」 | 用户生成 Key，外部客户端连 `:3002/mcp` |
| English 平台 AI → 外部 MCP | 「外部 MCP」 | 服务端 MCP Client 连 sidecar |

---

## 3. 数据模型

### 3.1 表 `mcp_template`（管理员维护）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(30)` PK | nanoid |
| `alias` | `String(32)` UNIQUE | `fetch` / `wikipedia` / `youtube` |
| `display_name` | `String(64)` | 如「读网页 Fetch」 |
| `description` | `Text` | 设置页展示说明 |
| `url` | `String(512)` | HTTP MCP 端点，如 `http://fetch-mcp:8080/mcp` |
| `header_schema` | `JSONB` | 用户需填的 Header 定义，见 §3.3 |
| `globally_enabled` | `Boolean` | 管理员总开关；`false` 时用户不可启用 |
| `enabled_roles` | `JSONB` | 默认 `["normal"]` |
| `tools_cache` | `JSONB` nullable | 管理员「测试连接」后缓存的 `list_tools` 结果 |
| `exposed_tools` | `JSONB` nullable | Admin 配置要暴露的工具名列表；`null` 时默认取 `tools_cache` 中**前 3 个**（见 §5.6） |
| `fetch_url_allowlist` | `JSONB` nullable | 仅 `alias=fetch` 使用：允许抓取的域名后缀，见 §8 |
| `last_synced_at` | `DateTime` nullable | 上次同步工具列表 |
| `sort_order` | `Int` | 设置页排序 |
| `created_at` / `updated_at` | `DateTime` | |

**Seed（迁移后）**：插入三条 `alias=fetch|wikipedia|youtube`，`globally_enabled=false`，URL 指向 compose 内网服务名；`fetch` 模板附带默认 `fetch_url_allowlist`（见 §8.2）。**不提供 POST 创建第四条模板**——本阶段仅维护 seed 三条。

### 3.2 表 `user_mcp_connection`（用户启用）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(30)` PK | nanoid |
| `user_id` | `String(30)` FK → `user.id` | |
| `template_id` | `String(30)` FK → `mcp_template.id` | |
| `enabled` | `Boolean` | 用户是否启用 |
| `headers_enc` | `Text` nullable | Fernet 加密的 JSON，用户填的 Header 值 |
| `tools_cache` | `JSONB` nullable | 用户「测试连接」后缓存的 `list_tools`（含个人 Header 时必需） |
| `last_tested_at` | `DateTime` nullable | 用户上次点「测试连接」 |
| `created_at` / `updated_at` | `DateTime` | |

**约束**：`(user_id, template_id)` UNIQUE；每用户每种模板最多一条连接。

**tools_cache 分层**：

| 场景 | 使用哪份缓存 |
|------|--------------|
| 模板无必填 Header（Fetch/Wikipedia 内网） | 优先 `mcp_template.tools_cache`；用户 connection 可无缓存 |
| 模板有必填 Header 或用户填写了 Header | **必须**有 `user_mcp_connection.tools_cache`（用户点「测试连接」后写入）；未测试则不挂载该 MCP 工具 |

### 3.3 Header Schema 示例

```json
{
  "fields": [
    {
      "key": "Authorization",
      "label": "API Key（可选）",
      "required": false,
      "secret": true,
      "placeholder": "Bearer xxx 或留空"
    }
  ]
}
```

- Fetch / Wikipedia：通常 **无必填 Key**（内网 sidecar）
- YouTube：若 sidecar 需要 Key，在 schema 中标记 `required: true`
- 用户保存时：仅存储 `fields[].key` → 用户输入值 的映射

### 3.4 工具命名

外部 MCP 工具挂载到 LangChain 时，前缀 **必须与 `mcp_template.alias` 完全一致**：

```
{alias}__{original_tool_name}
```

示例：`fetch__fetch_url`、`wikipedia__search`、`youtube__get_transcript`

（禁止缩写 alias，如 `wiki__` — 与 DB 不一致会导致 prompt 与工具名对不上。）

---

## 4. 主 API

### 4.1 Admin — `/api/v1/admin/mcp-templates`

**仅维护 seed 三条**，无 `POST ""` 创建接口。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `""` | 模板列表（含 tools_cache 摘要） |
| `GET` | `/{id}` | 详情 |
| `PUT` | `/{id}` | 更新 url、description、globally_enabled、header_schema、`exposed_tools`、`fetch_url_allowlist`（仅 fetch） |
| `POST` | `/{id}/test` | 无用户 Header 测试 `list_tools`，写回 `mcp_template.tools_cache` |

Admin 更新 `url` 时校验 host 为 Docker 内网服务名或白名单域名。

需 `get_current_admin`。

### 4.2 用户 — `/api/v1/user/external-mcp`

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `""` | 返回所有 **globally_enabled** 模板 + 当前用户的 connection 状态（不含 secret 明文） |
| `PUT` | `/{templateAlias}` | 创建/更新连接：`{ enabled, headers: { "Authorization": "..." } }` |
| `POST` | `/{templateAlias}/test` | 用用户 headers 测试连接，写回 `user_mcp_connection.tools_cache` 与 `last_tested_at` |
| `DELETE` | `/{templateAlias}` | 禁用并清除 headers |

需 JWT。响应中 secret 字段只返回 `••••` 或 `configured: true`。

**Service 层**：

- `app/services/mcp_template.py` — Admin CRUD、sync tools
- `app/services/user_mcp_connection.py` — 用户连接、加解密 headers
- `shared/mcp_crypto.py` — Fernet 加解密（密钥来自 `SECRET_KEY` 派生）

---

## 5. AI 服务集成

### 5.1 新模块

| 文件 | 职责 |
|------|------|
| `ai/services/mcp_client.py` | HTTP MCP Client：`connect`、`list_tools`、`call_tool`；超时 30s |
| `ai/services/mcp_url_guard.py` | Fetch 目标 URL 域名白名单 + DNS 解析后私网拦截 |
| `ai/services/tools/external_mcp.py` | 读 DB → 为每个 enabled 连接生成 LangChain `StructuredTool` |
| `ai/services/mcp_tool_cache.py` | 进程内短 TTL 缓存（如 5min）tools 列表，减轻 list_tools 压力 |

### 5.2 扩展工具加载（async，与现有同步 `make_tools` 配合）

现有 `make_tools()` / `make_tools_by_role()` 为 **同步函数**，不可在内部 `await`。采用 **chat 层 preload**：

```python
# ai/services/chat.py（stream_chat 内）
external_tools = await load_external_mcp_tools(user_id)  # 仅 role==normal 时调用
tools = make_tools_by_role(
    user_id, role, conversation_id,
    external_tools=external_tools,  # 新增可选参数
    ...
)
```

```python
# ai/services/tools/__init__.py
def make_tools(..., external_tools: list | None = None) -> list:
    tools = [...existing built-in tools...]
    if external_tools:
        tools.extend(external_tools)
    return tools

def make_tools_by_role(..., external_tools: list | None = None) -> list:
    if role == "normal":
        return make_tools(..., external_tools=external_tools)
    ...
```

`load_external_mcp_tools(user_id)` 逻辑：

1. 查 `user_mcp_connection` JOIN `mcp_template` WHERE `enabled=true` AND `globally_enabled=true` AND `'normal' IN enabled_roles`
2. 对每个连接：按 §3.2 规则取 `tools_cache`（模板级或用户级）；缓存缺失且需要 Header 则 **跳过** 该连接
3. 缓存过期（TTL 5min，见 §5.3）时 MCP Client 刷新并写回 DB
4. 按 §5.6 过滤 `exposed_tools` 后，每个 remote tool 包装为 LangChain tool，名称 `{alias}__{name}`，handler 内 `call_tool`（Fetch 调用前走 §8 URL 校验）

### 5.3 缓存策略（非 Agent 缓存）

**`normal` 角色 `agent_cache_key` 已为 `None`**（每条消息重建 agent），无需为外部 MCP 改 agent 缓存。

需缓存的是 **`list_tools` 结果**，避免每条消息都连 sidecar：

| 层级 | 机制 |
|------|------|
| DB | `mcp_template.tools_cache` / `user_mcp_connection.tools_cache`（持久，测试连接时更新） |
| 进程内 | `mcp_tool_cache.py` TTL 5min，key = `(template_id, user_id, connection.updated_at)` |

用户修改 Header 或 `enabled` 后：`updated_at` 变化 → 进程缓存失效；有 Header 的模板需重新「测试连接」。

### 5.4 错误处理

| 场景 | 行为 |
|------|------|
| MCP 超时 | tool 返回 `{ "error": "外部服务超时，请稍后重试" }` |
| MCP 4xx/5xx | 记录日志，tool 返回可读错误，不中断 SSE |
| 用户未启用 | 不挂载该 MCP 工具 |
| 模板 globally_enabled=false | 用户设置页灰显，API 拒绝启用 |
| 有 Header 但未 test | 不挂载该 MCP 工具，设置页提示「请先测试连接」 |

### 5.5 System Prompt 补充（normal）

在现有 prompt 末尾追加简短说明（由 `prompt_loader` 注入）：

> - 用户粘贴 **具体英文网页 URL** 时，用 `fetch__` 前缀工具读取正文，再结合查词/语法讲解。  
> - 用户要 **某话题的英文百科背景**（无 URL）时，用 `wikipedia__` 前缀工具。  
> - 用户提供 **YouTube 链接** 练听力时，用 `youtube__` 前缀工具取字幕。  
> - 问 **平台课程/站内知识** 时仍用 `knowledge_search`，不要用外部 MCP。  
> - 问 **实时新闻/天气** 时仍用联网搜索，不要用 fetch。

**链式调用说明**：上述「fetch 后再查词/加生词本」依赖模型 **多次 tool call**，非框架强制。各 external tool 的 `description` 应写明后续建议（如「返回正文后请继续用 word_lookup 解释难词」）；用户也可在一句话里明确要求全流程。

### 5.6 工具数上限（DeepSeek 隐式限制）

| 类别 | 数量策略 |
|------|----------|
| 内置工具（查词、语法等） | 保持现有 ~7 个，不增 |
| 外部 MCP 每模板 | **默认最多暴露 3 个** tool |
| 外部 MCP 合计 | 三模板全开时 **≤9 个** external + ~7 内置 ≈ **≤16 个** |

**`exposed_tools` 规则**（`mcp_template` 字段）：

- Admin 在「测试连接」后可勾选要暴露的工具；保存为 `exposed_tools: string[]`（原始 tool 名，不含前缀）
- `null` 或未配置：取 `tools_cache` 中按名称排序的 **前 3 个**
- `load_external_mcp_tools` 只挂载 `exposed_tools` 列表内的 tools

Admin UI：测试连接后展示全部 tools，checkbox 多选，默认勾选前 3 个。

---

## 6. 部署：MCP Sidecar 容器

官方 Fetch/Wikipedia/YouTube MCP 多为 stdio；生产在 `deploy/docker-compose.yml` 增加 sidecar（**实施前先 spike 镜像**，见 §12）。

| 服务名 | 用途 | 网络 |
|--------|------|------|
| `fetch-mcp` | 网页抓取 MCP HTTP 网关 | 仅 Docker 内网 |
| `wikipedia-mcp` | 维基 MCP HTTP 网关 | 仅 Docker 内网 |
| `youtube-mcp` | YouTube 字幕 MCP HTTP 网关 | 仅 Docker 内网 |

- **不暴露** 到 Nginx 公网
- `ai` 服务 `depends_on` 上述服务（sidecar 不可用时对应工具静默不可用）
- **资源与内存（P0 必验，见 §6.1）**：
  - 当前 ECS `ai` 限 **1536M**；三 sidecar 各 128–256M → 额外 **384–768M**
  - 全栈（nginx + app + ai + mcp + postgres + minio + sidecar）约 **2.5–3.5GB**
  - **若 ECS 无法升配至 ≥4GB**：P0 必须改方案（单 `mcp-gateway` 合并 sidecar / 仅上 Fetch 一个 sidecar / 暂缓外部 MCP）
- Admin 模板 seed URL 使用 Docker DNS 主机名

**本地开发**：`deploy/docker-compose.yml` 同上 sidecar；无 compose 时 Admin 将模板 `globally_enabled=false`，外部 MCP 功能跳过。

### 6.1 P0 Spike 验收标准（**P1 代码前置，未通过不得开工 P1**）

P0 **Done** 当且仅当以下四项全部满足，结论写入 `docs/external-mcp-setup.md`：

| # | 验收项 | 通过标准 |
|---|--------|----------|
| 1 | **HTTP 网关方案** | 选定一种（社区 `mcp-proxy` / 自研 stdio→HTTP 薄包装 / 单容器 `mcp-gateway`），本地 `docker compose` 可复现 |
| 2 | **Fetch sidecar 联通** | 从 `ai` 容器同网络 `list_tools` 成功；`call_tool` 抓取公网测试 URL（如 `https://example.com`）成功 |
| 3 | **ECS 内存决策** | 在目标 ECS 上 `docker stats` 测全栈峰值；输出书面结论：**升配至 ≥4GB** / **合并 gateway** / **缩减 scope** 三选一 |
| 4 | **SSRF  spike** | Fetch URL 校验原型：域名白名单 + DNS 解析后拒绝私有 IP 的单测通过 |

**P0 不交付**：Admin API、用户设置页、DB 迁移等业务代码。

### 6.2 Phase 分期

| Phase | 交付 |
|-------|------|
| **P0** | §6.1 四项 spike 验收 + 文档 |
| **P1** | 框架 + Admin/User API + 设置页 UI + **Fetch** 联调（依赖 P0） |
| **P2** | **Wikipedia** sidecar + 联调 |
| **P3** | 调研 YouTube HTTP MCP；可行则接入，否则文档记录阻塞项 |

---

## 7. 前端

### 7.1 Web 设置页（`apps/web/src/views/Setting/index.vue`）

在现有「MCP 连接」卡片旁新增 **「外部 MCP」** 区域（或 Tab）：

每个模板一张卡片：

- 标题 + description
- 开关（`el-switch`）— 仅 `globally_enabled` 时可操作
- 动态表单：按 `header_schema.fields` 渲染输入框（secret 用 password）
- 按钮：**保存**、**测试连接**
- 测试成功展示该用户/模板 `tools_cache` 中的工具名列表（只读）
- 有必填 Header 且未测试成功时，开关可开但聊天侧不挂载，并提示「请先测试连接」

API 模块：`apps/web/src/apis/external-mcp/index.ts`  
类型：`packages/common/external-mcp/index.ts`

### 7.2 Admin（`apps/admin`）

新路由 `/mcp-templates`：

- 表格：alias、display_name、globally_enabled、last_synced_at
- 编辑抽屉：url、description、header_schema（JSON 编辑器或简化表单）、**exposed_tools 多选**（测试连接后）、fetch 模板额外 **fetch_url_allowlist**
- **测试连接** / **刷新工具**

---

## 8. 安全

### 8.1 SSRF — Admin 配置的 MCP URL

用户 **不可** 改 URL。Admin 更新 `url` 时校验 host 为 Docker 内网 sidecar 主机名（`fetch-mcp`、`wikipedia-mcp` 等）或运维白名单。

### 8.2 SSRF — Fetch 抓取用户/Agent 传入的目标 URL（**白名单优先**）

黑名单（RFC1918、loopback、link-local、元数据 IP）**仅作兜底**，不足以单独依赖（IPv6 映射 `::ffff:127.0.0.1`、DNS rebinding、云厂商新元数据端点等可绕过）。

**P1 默认策略（按顺序执行）**：

1. **域名白名单**（`mcp_template.fetch_url_allowlist`）：仅允许后缀匹配，seed 默认：
   ```json
   ["bbc.com", "bbc.co.uk", "wikipedia.org", "medium.com", "nationalgeographic.com", "youtube.com", "youtu.be"]
   ```
   Admin 可增删。非白名单域名 → tool 返回 `{ "error": "该域名不在允许列表" }`，不调用 sidecar。

2. **协议**：仅 `http://` / `https://`；拒绝 `file://`、`ftp://` 等。

3. **DNS 解析后验**（在 AI 服务 `call_tool` 前，或 sidecar 内）：解析 A/AAAA 记录，若任一为私有/保留/loopback/link-local → 拒绝。

4. **黑名单兜底**：拒绝 RFC1918、`127.0.0.0/8`、`169.254.0.0/16`、`::1`、`fc00::/7` 等。

5. **禁止重定向到内网**：若 sidecar 跟随重定向，需对每个跳转 URL 重复 1–4（sidecar 实现或 AI 层限制不跟随重定向）。

Wikipedia / YouTube sidecar 由 MCP 自身固定 API 端点，不接收任意 URL，SSRF 风险低于 Fetch。

### 8.3 其他

| 风险 | 措施 |
|------|------|
| 凭证泄露 | headers Fernet 加密存 DB；API 不回显明文；日志打码 |
| 工具滥用 | 单用户单对话 external MCP 调用上限（如 10 次/轮，可选 P2） |
| 内网扫描 | sidecar 不映射 host 端口 |

---

## 9. 典型用户流程

### 9.1 读英文网页（Fetch）

1. 管理员启用 Fetch 模板，`globally_enabled=true`
2. 用户在设置页打开 Fetch 开关 → 保存（无需 Key）
3. 聊天（normal）：「请读 https://bbc.com/... 并标难词」
4. **理想路径**（非保证）：Agent 调用 `fetch__*` 取正文 → 再调 `word_lookup` 解释难词 → 用户确认后加入生词本

**说明**：模型可能只执行第 4 步中的 fetch 即回复。提高链式调用概率的方式：§5.5 prompt、external tool description、用户一句说清「读完后标难词并加入生词本」。

### 9.2 维基阅读（Wikipedia）

1. 用户启用 Wikipedia
2. 「用简单英文介绍 the Industrial Revolution」
3. Agent 调用 `wikipedia__*` 取文 → 讲解

### 9.3 YouTube 字幕

1. 用户启用 YouTube（若模板可用）
2. 粘贴 `https://youtube.com/watch?v=...`
3. Agent 调用 `youtube__*` 取字幕 → 听力讲解

---

## 10. 测试

| 层级 | 内容 |
|------|------|
| 单元 | header 加解密；工具名前缀；Fetch URL 白名单 + DNS 私网拦截；`exposed_tools` 默认 3 个；list_tools TTL 缓存 key |
| 集成 | `scripts/smoke_external_mcp_api.py` — Admin 改模板、用户启用、test 连接 |
| 手动 | normal 聊天贴 BBC 链接；验证 fetch 工具被调用 |
| 回归 | 未启用外部 MCP 时，现有内置工具行为不变 |

---

## 11. 文件清单（实现参考）

| 新建 | 修改 |
|------|------|
| `app/models/mcp_template.py`, `user_mcp_connection.py` | `app/models/__init__.py`, `alembic/env.py` |
| `app/services/mcp_template.py`, `user_mcp_connection.py` | |
| `app/routers/admin/mcp_templates.py` | `app/routers/admin/__init__.py` |
| `app/routers/external_mcp.py` | `app/main.py` |
| `shared/mcp_crypto.py` | |
| `ai/services/mcp_client.py`, `mcp_url_guard.py`, `tools/external_mcp.py` | `ai/services/tools/__init__.py`, `ai/services/chat.py` |
| `packages/common/external-mcp/index.ts` | |
| `apps/web/src/apis/external-mcp/` | `apps/web/src/views/Setting/index.vue` |
| `apps/admin/src/views/mcp-templates/` | `apps/admin/src/router/index.tsx` |
| `deploy/docker-compose.yml`（sidecar） | `deploy/env.production.example` |
| `docs/external-mcp-setup.md` | `AGENTS.md`（一句） |

---

## 12. 开放问题（P0/P1 前验证）

1. **Sidecar 镜像**：Fetch/Wikipedia 可用社区 `mcp-proxy`、自研薄 HTTP 包装 stdio、或单容器 `mcp-gateway` — **由 §6.1 P0 spike 关闭，不再阻塞 P1**
2. **ECS 内存**：**由 §6.1 P0 第 3 项关闭**；若无法 ≥4GB 则 P1 scope 缩减为单 Fetch sidecar 或暂缓
3. **YouTube HTTP MCP**：P3 验证；无稳定方案则 Admin 占位 + 文档说明
4. ~~DeepSeek 工具数上限~~ → 已由 §5.6 `exposed_tools` 默认每模板 3 个关闭

---

## 13. 修订记录

| 日期 | 变更 |
|------|------|
| 2026-06-30 | 初稿：方案 B + Fetch/Wikipedia/YouTube |
| 2026-06-30 | 自检修订：async preload、前缀统一、list_tools 缓存分层、无 POST 创建模板 |
| 2026-06-30 | mimo review：§6.1 P0 四项验收（含 ECS 内存）、§8.2 白名单优先 SSRF、§5.6 exposed_tools 默认 3、§9.1 链式调用非保证 |

---

**审阅请确认**：修订后 spec 是否符合预期。确认后进入实现计划（`writing-plans`）。

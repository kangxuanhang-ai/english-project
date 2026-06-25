# B 端管理后台 + 知识库 RAG 设计

> 状态：**v4 已评审** — 实现计划：[2026-06-24-admin-knowledge-base.md](../plans/2026-06-24-admin-knowledge-base.md)

## 概述

在现有英语学习平台（C 端 Vue 3 + 双 FastAPI 后端）基础上，新增 **B 端运营管理后台**，核心能力为 **知识库上传与向量检索（RAG）**，检索结果供 C 端 `normal` 角色 AI 对话调用。

| 模块 | 一句话 |
|------|--------|
| 仪表盘 | 用户、订单、知识库、PV 等运营概览 |
| 用户管理 | 列表搜索 + 详情（只读） |
| 课程管理 | CRUD + 软下架（`is_published`） |
| 订单管理 | 支付记录查询与筛选（只读） |
| 数据监控 | PV/UV 趋势、错误日志、Web Vitals |
| **知识库** | 上传 txt/md/pdf/docx → 向量化 → AI `knowledge_search` 检索 |

**已确认的产品决策：**

- 方案 **A**：独立 `apps/admin` + PostgreSQL **pgvector** + MinIO 原件存储 + DeepSeek Embedding。
- B 端技术栈：**React 18 + Ant Design 5 + Vite**，端口 **8081**。
- 管理员：**单一管理员账号**，复用 `POST /api/v1/user/login`，`User.role = admin`；无独立账号体系、无提权界面。
- Embedding：**DeepSeek Embedding API**；维度 **配置化**，Phase 0 实测后写入 `EMBEDDING_DIMENSIONS`。
- 课程下架：字段 **`is_published`**（`true` 上架 / `false` 下架），非硬删。
- 用户管理：**只读**，不支持禁用账号。
- 知识库单文件上限：**20MB**；格式：`.txt` `.md` `.pdf` `.docx`。
- 知识库上传：**支持批量队列**；课程封面一期仍手动填 `url`。
- 数据监控：**一个侧栏菜单 + Tab**（流量 / 错误 / 性能）。
- C 端聊天：**一期不展示来源引用卡片**。

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│  apps/admin (React :8081)          apps/web (Vue :8080)                  │
│  仪表盘 / 用户 / 课程 / 订单 / 监控 / 知识库          AI 聊天 normal 角色   │
└───────────────┬──────────────────────────────────────┬──────────────────┘
                │ /api/v1/admin/*                      │ /ai/v1/chat (SSE)
                ▼                                      ▼
┌───────────────────────────────┐      ┌──────────────────────────────────┐
│  server/app (3000)            │      │  server/ai (3001)                 │
│  routers/admin/*              │      │  tools/knowledge_search           │
│  services/knowledge/          │      │  （读 knowledge_chunk + pgvector）│
│    upload / ingest / search   │      └──────────────────┬───────────────┘
└───────────────┬───────────────┘                         │
                │                                         │
                ▼                                         ▼
        ┌───────────────┐                    ┌─────────────────────┐
        │  MinIO         │                    │  PostgreSQL (english) │
        │  knowledge/    │                    │  + pgvector extension │
        │  {docId}/file  │                    │  knowledge_document   │
        └───────────────┘                    │  knowledge_chunk      │
                                             │  user / course / ...  │
                                             └─────────────────────┘
```

**不动的部分：** C 端 `apps/web` 不加 admin 路由；ClickHouse 仍不使用（埋点查 Postgres）；AI Prompt 在线编辑不在本期。

**新增/改动边界：**

| 单元 | 职责 |
|------|------|
| `apps/admin` | 全新 B 端 SPA |
| `server/app/routers/admin/` | 管理员 API，`/api/v1/admin/*` |
| `server/app/services/knowledge/` | 上传、解析、分块、向量化、检索 |
| `server/ai/services/tools/knowledge.py` | AI 检索工具（仅 `normal` 角色） |
| `packages/common` | admin / knowledge 共享 TypeScript 类型 |
| `packages/config` | 新增 admin 端口 `8081` |

---

## 认证与权限

### User 表扩展

```python
role: Mapped[str] = mapped_column(String, default="user")  # "user" | "admin"
```

- 种子数据预置 **1 个管理员账号**（如 `phone: 13800000000`，`role: admin`）。
- 普通注册用户默认 `role=user`；**一期不提供提权界面**。
- B 端登录页调用 `POST /api/v1/user/login`；登录成功后前端检查 `role === 'admin'`，否则提示无权限并清除 token。
- 新增依赖 `get_current_admin`：校验 JWT + `role == admin`。
- 所有 `/api/v1/admin/*` 强制 `get_current_admin`；非 admin 返回 **403**。

### CORS

`CORS_ORIGINS` 增加 `http://localhost:8081`；生产环境增加 admin 域名。

---

## 数据模型

### Course 表扩展（软下架）

```python
is_published: Mapped[bool] = mapped_column(Boolean, default=True)
```

- **上架**：`is_published=true`，C 端课程列表可见。
- **下架**：`is_published=false`，C 端商城列表不可见；**已购用户「我的课程」仍可见、可学习**。
- 管理端不提供硬删；有历史购课记录的课程只允许下架。

### 知识库 — `knowledge_document`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string(30) | nanoid |
| title | string(200) | 显示标题，**必填**，最长 200 字符，**可重复**；上传未传时用去扩展名的 `filename` 填充 |
| filename | string | 原始文件名 |
| mime_type | string | 如 `application/pdf` |
| file_size | int | 字节 |
| minio_key | string | `knowledge/{documentId}/{filename}`，其中 `{documentId}` 即本文档 `id` |
| status | DocumentStatus | 见下文状态枚举 |
| chunk_count | int | 默认 0；ready 后写入 |
| error_message | text? | 失败原因，**最长 500 字符** |
| uploaded_by | FK user.id, **NOT NULL** | 上传者（一期均为管理员；未来系统自动上传再评估是否可空） |
| created_at / updated_at | datetime | `updated_at` 在**标题修改**、**status 变更**时更新（ORM `onupdate`） |

### 知识库 — `knowledge_chunk`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string(30) | nanoid |
| document_id | FK | 级联删除 |
| chunk_index | int | 文档内序号，从 0 起 |
| content | text | 分块文本 |
| embedding | vector(N) | N = `EMBEDDING_DIMENSIONS`（配置项，不写死） |
| token_count | int | ingestion 时按 chunk 内容估算 token 数并写入 |
| created_at | datetime | — |

**索引：**

- `knowledge_chunk.document_id`
- `knowledge_chunk.embedding`：**HNSW** + `vector_cosine_ops`（一期数据量小；>10 万文档可评估 IVFFlat）

### 状态枚举

```python
class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
```

### 状态流转

```
上传 MinIO 成功 → 写 DB status=pending → 投递后台任务
后台任务启动     → processing
解析+向量化成功   → ready（写入 chunk_count）
任意失败         → failed（error_message[:500]）
```

**特殊情况：** 解析后 chunk 数量为 0（空文件）→ `failed`，`error_message="文档内容为空"`。

---

## 知识库 ingestion 流水线

### 上传校验

同时校验 **扩展名** 与 **MIME**（任一不通过返回 400）：

| 扩展名 | MIME |
|--------|------|
| `.txt` | `text/plain` |
| `.md` | `text/markdown` |
| `.pdf` | `application/pdf` |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |

- 扩展名小写归一化后比对白名单。
- 单文件 ≤ **20MB**（`KNOWLEDGE_MAX_FILE_SIZE`）。

### 并发限制

上传与 reindex 接口在 API 层检查：

```python
processing_count = await db.scalar(
    select(func.count()).where(KnowledgeDocument.status == DocumentStatus.PROCESSING)
)
if processing_count >= 3:
    raise HTTPException(429, "同时处理的文档已达上限，请稍后重试")
```

**批量上传：** 前端 `Upload.Dragger` 可选多文件，但后端**逐个受理**——每个文件独立走「MinIO → DB pending → BackgroundTask」；全局仍受 processing ≤ 3 限制，超出 429 的文件留在前端队列等待重试。**单个文件失败（校验失败、429、ingestion failed）不影响其他文件继续处理**；前端按文件展示各自成功/失败状态。

### 处理流程

1. 上传文件 → MinIO `knowledge/{documentId}/{filename}`
2. 写 `knowledge_document`（`status=pending`）
3. `BackgroundTasks` 启动 ingestion：
   - `status → processing`
   - 从 MinIO 拉原件
   - 解析：`pymupdf`（PDF）、`python-docx`（DOCX）、纯文本（TXT/MD）
   - 分块：LangChain `RecursiveCharacterTextSplitter`，`chunk_size=500`，`overlap=50`
   - 调用 DeepSeek Embedding API；校验 `len(embedding) == EMBEDDING_DIMENSIONS`
     - **不匹配时**：`status=failed`，`error_message="Embedding 维度不匹配"`，删除已写入 chunk，不继续入库
   - 批量写入 `knowledge_chunk`（含 `token_count`）
   - `status → ready`，更新 `chunk_count`
4. 全程 `try/except`：异常时 `status=failed`，`error_message=str(e)[:500]`，删除本次已写入的 chunk（若有）；**仅影响当前文档**

### reindex（全量重建，非增量）

1. 检查并发 processing 上限
2. `status → processing`
3. **删除该文档全部旧 chunk**
4. 从 MinIO 重新拉原件 → 走完整解析/分块/向量化流程
5. 成功 → `ready`；失败 → `failed`

### 删除文档

顺序：

1. **先删 DB**（`knowledge_document`，chunk 级联删）
2. **再删 MinIO** 原件

MinIO 删除失败：`logger.warning`，**不回滚 DB**。DB 删除失败：返回错误，不删 MinIO。

---

## 知识库检索返回格式

管理员测试检索与 AI 工具内部格式统一：

```json
{
  "results": [
    {
      "content": "片段内容...",
      "title": "文档标题",
      "score": 0.85,
      "documentId": "xxx",
      "chunkIndex": 5
    }
  ],
  "query": "用户输入的查询",
  "totalTokens": 1500
}
```

- 仅检索 `status=ready` 的文档所属 chunk。
- 默认 Top-K=5；按余弦相似度降序取 Top-K 后，**过滤 `score < KNOWLEDGE_MIN_SCORE`（默认 0.5，可配置）** 的结果，避免返回不相关片段；过滤后为空则 `results: []`。
- `totalTokens` 为 results 内容 token 估算总和。
- AI 工具注入上下文时，results 总字符仍遵守 **≤3000 字** 上限。

---

## Admin API 清单

前缀 `/api/v1/admin`，均需 `get_current_admin`。

### 仪表盘

`GET /admin/dashboard`

```json
{
  "userCount": 128,
  "todayNewUsers": 3,
  "courseCount": 8,
  "todayOrders": 2,
  "totalRevenue": 156.00,
  "todayRevenue": 16.00,
  "knowledgeDocCount": 12,
  "knowledgeReadyCount": 10,
  "todayPv": 456,
  "todayUv": 89,
  "recentErrors": 3
}
```

数据来源：`user`、`payment_record`（`TRADE_SUCCESS`）、`knowledge_document`、`page_view`、`visitor`、`error_entry`。

### 用户管理（只读）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/users` | `?page&pageSize&keyword`（name/phone/email） |
| GET | `/admin/users/{id}` | 基本信息 + 掌握词数 + 已购课程 + 最近登录 |

### 课程管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/courses` | 分页列表（含 `is_published`） |
| POST | `/admin/courses` | 新建 |
| PUT | `/admin/courses/{id}` | 编辑 |
| PUT | `/admin/courses/{id}/publish` | `is_published=true` 上架 |
| PUT | `/admin/courses/{id}/unpublish` | `is_published=false` 下架 |

请求体字段：`name, value, description, teacher, url, price`。

**C 端改动：** `GET /api/v1/course/list` 仅返回 `is_published=true`。

### 订单管理（只读）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/orders` | `?page&pageSize&status&startDate&endDate&keyword` |
| GET | `/admin/orders/{id}` | 详情 + 关联课程 |

### 数据监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/analytics/overview` | 近 7/30 天 PV/UV 趋势 |
| GET | `/admin/analytics/pages` | 页面 PV Top 20 |
| GET | `/admin/analytics/errors` | 错误列表，分页，时间倒序 |
| GET | `/admin/analytics/performance` | Web Vitals 均值 |

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/knowledge` | 见下方「列表查询约定」 |
| POST | `/admin/knowledge/upload` | multipart: `file` + 可选 `title`（未传则用去扩展名的文件名） |
| PUT | `/admin/knowledge/{id}` | 改标题（非空，`len ≤ 200`） |
| DELETE | `/admin/knowledge/{id}` | 删文档（DB → MinIO） |
| POST | `/admin/knowledge/{id}/reindex` | 全量重建向量 |
| GET | `/admin/knowledge/{id}` | 文档详情（元信息，字段见实施计划） |
| GET | `/admin/knowledge/search` | `?q=&topK=5` 检索测试 |
| GET | `/admin/knowledge/{id}/chunks` | 分块列表，`?page&pageSize`（默认 1/20）；字段见实施计划 |
| GET | `/admin/knowledge/{id}/download` | 原件下载；**实施时在「MinIO 预签名 URL」与「后端流式代理」中选定一种** |

**列表查询约定（`GET /admin/knowledge`）：**

| 参数 | 说明 |
|------|------|
| `page` / `pageSize` | 分页，默认 `1` / `10` |
| `keyword` | 模糊匹配 **`title`**（`ILIKE %keyword%`） |
| `status` | 筛选：`pending` / `processing` / `ready` / `failed` |
| 默认排序 | **`created_at DESC`**（最新上传在前） |

**标题约束：**

- 必填；上传时未传 `title` → 后端用去扩展名的 `filename` 自动填充
- 最长 **200** 字符；允许不同文档使用相同标题
- `PUT` 改标题时校验非空 + 长度，否则返回 400

---

## AI 集成

### 新工具 `knowledge_search`

**文件：** `server/ai/services/tools/knowledge.py`

挂到 `normal` 角色的 `make_tools`：

```python
@tool
async def knowledge_search(query: str) -> str:
    """从平台知识库检索与学习相关的内部资料。
    优先用于：课程说明、学习方法论、平台规则、教研内容等。
    查单词用 word_lookup，实时新闻用 web_search。"""
```

- query → DeepSeek Embedding → pgvector 余弦相似度 Top-K → 按 `KNOWLEDGE_MIN_SCORE` 过滤
- 仅 `status=ready` 的文档
- 返回上述 JSON 字符串（截断后）
- AI 服务通过共享 `DATABASE_URL` 读 `knowledge_chunk`

**C 端：** 一期不改聊天气泡 UI；AI 自然引用内容即可。

---

## B 端前端 `apps/admin`

### 技术栈

| 项 | 选型 |
|----|------|
| 框架 | React 18 + Vite + TypeScript |
| UI | Ant Design 5 |
| 路由 | React Router 6 |
| 请求 | Axios + TanStack Query |
| 登录态 | Zustand + localStorage |
| 图表 | @ant-design/charts 或 ECharts |
| 共享包 | `@en/common`、`@en/config` |
| 端口 | 8081 |

### 目录结构

```
apps/admin/
├── src/
│   ├── apis/
│   ├── layout/AdminLayout.tsx
│   ├── views/
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── users/List.tsx, Detail.tsx
│   │   ├── courses/List.tsx, Form.tsx
│   │   ├── orders/List.tsx, Detail.tsx
│   │   ├── analytics/Overview.tsx    # Tab: 流量 / 错误 / 性能
│   │   └── knowledge/List.tsx, Search.tsx, Detail.tsx
│   ├── router/
│   ├── stores/user.ts
│   └── main.tsx
```

### 路由

| 路径 | 页面 |
|------|------|
| `/login` | 登录 |
| `/` | 仪表盘 |
| `/users`, `/users/:id` | 用户列表 / 详情 |
| `/courses`, `/courses/new`, `/courses/:id/edit` | 课程 |
| `/orders`, `/orders/:id` | 订单 |
| `/analytics` | 数据监控（三 Tab） |
| `/knowledge`, `/knowledge/search`, `/knowledge/:id` | 知识库 |

### 侧栏菜单顺序

```
仪表盘
知识库          ← 核心，第二位
用户管理
课程管理
订单管理
数据监控
```

### 知识库页面要点

- **列表：** `Upload.Dragger` 批量上传（后端逐个处理）；表格含 status Tag；**当列表中存在 `processing` 文档时，前端每 3s 调用 `GET /admin/knowledge` 刷新列表**，全部就绪后停止轮询；操作：reindex / 预览分块 / 删除
- **检索测试：** 搜索框 + TopK；结果卡片展示 score、title、content 高亮
- **详情：** 调用 `GET /admin/knowledge/{id}` 展示元信息；`GET /admin/knowledge/{id}/chunks` 展示分块列表（content 前 200 字预览）；响应字段在实施计划中定义

### 路由守卫

- 未登录 → `/login`
- 已登录 `role !== admin` → 提示无权限，清除 token

### 根脚本

`package.json` 新增：

```json
"admin": "pnpm --filter @en/admin dev"
```

`pnpm all` 可选扩展为 web + admin + server + ai。

---

## 环境与依赖

### 环境变量（`server/.env`）

```env
DEEPSEEK_EMBEDDING_MODEL=deepseek-embed    # 以 DeepSeek 官方文档为准
EMBEDDING_DIMENSIONS=1536                  # 占位值；Phase 0 实测 API 后确认（可能为 1024 / 1536 / 2048，以返回为准）
KNOWLEDGE_MAX_FILE_SIZE=20971520           # 20MB
KNOWLEDGE_CHUNK_SIZE=500
KNOWLEDGE_CHUNK_OVERLAP=50
KNOWLEDGE_MIN_SCORE=0.5                 # 检索最低相似度阈值（余弦相似度，0~1）
```

`CORS_ORIGINS` 增加 `http://localhost:8081`。

### Python 依赖（`server/pyproject.toml`）

```toml
"pymupdf>=1.24.0"
"python-docx>=1.1.0"
"pgvector>=0.3.0"
```

Embedding 调用沿用 `httpx` 直调 DeepSeek `/v1/embeddings`（与 `llm.py` 风格一致）。

### PostgreSQL pgvector（Phase 0 必做）

1. 确认已安装 pgvector 扩展（Docker 使用 `pgvector/pgvector` 镜像）
2. Alembic 迁移首步：`CREATE EXTENSION IF NOT EXISTS vector;`
3. `EMBEDDING_DIMENSIONS` 经一次实测 API 确认后再创建 `knowledge_chunk` 表

---

## 实施分期

| Phase | 内容 | 产出 |
|-------|------|------|
| **0 — 地基** | `User.role`；`Course.is_published`；pgvector 扩展；`apps/admin` 脚手架；`/api/v1/admin` + `get_current_admin`；登录 + Layout；种子管理员；`EMBEDDING_DIMENSIONS` 实测 | 可登录空壳后台 |
| **1 — 运营** | 仪表盘、用户、课程 CRUD/下架、订单；C 端课程列表过滤 `is_published` | 4 个运营模块可用 |
| **2 — 知识库** | 知识库表、MinIO 上传、解析/分块/向量化、ingestion、知识库管理页 | B 端可上传至 ready |
| **3 — 闭环** | `knowledge_search` AI 工具、检索测试页、数据监控 Tab、C 端 RAG 实测 | 全链路跑通 |

**依赖：** Phase 2 依赖 Phase 0；Phase 3 AI 工具依赖 Phase 2；Phase 1 可与 Phase 2 部分并行。

---

## 风险与应对

| 风险 | 应对 |
|------|------|
| PostgreSQL 未装 pgvector | Phase 0 文档 + `pgvector/pgvector` 镜像 |
| DeepSeek Embedding 维度与配置不符 | Phase 0 实测；入库前校验维度 |
| DeepSeek API 不稳定 | `failed` + reindex；工具侧超时返回友好 JSON |
| 大 PDF 解析慢 | 20MB 上限；processing 并发 ≤3 |
| React + Vue 双栈 | 边界清晰，仅共享 `@en/common` 类型 |
| AI 误用知识库 | Tool description 明确边界 |
| 下架课程影响已购用户 | 「我的课程」仍展示已购 |

---

## 不在本期范围

- 多管理员 / 提权界面
- 用户禁用、订单手动改状态
- 课程封面上传
- 聊天气泡「来源引用」卡片
- 知识库 URL 导入、PPTX
- ClickHouse 迁移
- Celery / Redis 队列（一期 BackgroundTasks）
- AI Prompt 在线编辑

---

## 验收标准

### 基础

- [ ] 管理员可登录 `localhost:8081`；普通用户被拒绝
- [ ] 非 admin 访问 `/api/v1/admin/*` 返回 403

### 运营模块

- [ ] 仪表盘数据与 DB 一致
- [ ] 用户列表可搜索；详情含学习/购课概况
- [ ] 课程可新建/编辑/下架/上架；C 端列表不显示下架课；已购仍可学
- [ ] 订单可按状态、日期筛选

### 知识库

- [ ] 可上传四种格式（≤20MB）；状态 pending → processing → ready
- [ ] 扩展名与 MIME 双重校验生效
- [ ] 空文件 → failed「文档内容为空」
- [ ] 失败显示 error_message（≤500 字）；可 reindex
- [ ] 同时 processing 超过 3 个时上传返回 429
- [ ] 检索测试返回 results + query + totalTokens
- [ ] 删除后 DB 与检索均不可见

### AI 接入

- [ ] `normal` 角色可引用知识库内容作答
- [ ] 查词仍走 `word_lookup`，不误用知识库

### 监控

- [ ] PV/UV 趋势有数据（依赖 Tracker 埋点）
- [ ] 错误列表可查看 stack

---

## 已确认决策（评审记录）

| 决策 | 结论 |
|------|------|
| 整体方案 | A：独立 admin + pgvector |
| B 端框架 | React + Ant Design（非 Vue） |
| 管理员 | 单账号，`role=admin`，共用 login API |
| 课程下架字段 | `is_published`（非 `is_active`） |
| Embedding | DeepSeek；维度配置化，Phase 0 实测 |
| 用户管理 | 只读，无禁用 |
| 知识库上限 | 20MB |
| 删除顺序 | DB 先，MinIO 后；MinIO 失败仅日志 |
| reindex | 全量重建（删旧 chunk 再生成） |
| 向量索引 | HNSW |
| 并发 ingestion | API 层 DB 计数，上限 3 |
| 知识库列表 keyword | 模糊匹配 `title` |
| 知识库标题 | 必填，最长 200，可重复；未传 title 用 filename |
| 知识库列表排序 | 默认 `created_at DESC` |
| Embedding 维度不匹配 | `failed`，`error_message="Embedding 维度不匹配"` |
| 批量上传 | 前端多选，后端逐个受理；全局 processing ≤ 3 |
| 状态轮询 | 前端 3s 调 `GET /admin/knowledge` |
| 下载 API | 实施时选定预签名 URL 或流式代理 |
| uploaded_by | 一期 NOT NULL，必填管理员 ID |
| token_count | ingestion 时写入 |
| 相似度阈值 | `KNOWLEDGE_MIN_SCORE` 默认 0.5 |
| updated_at | 标题修改、status 变更时更新 |
| minio_key | `{documentId}` = 文档 id |
| 批量失败隔离 | 单文件失败不影响其他文件 |
| chunks 分页 | `?page&pageSize`，默认 1/20 |

---

## 文档修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1 | 2026-06-24 | 初稿：brainstorming 定稿 + 两轮审查意见合并 |
| v2 | 2026-06-24 | 补充：列表 keyword/排序、标题约束、Embedding 维度注释 |
| v3 | 2026-06-24 | 补充：维度失败处理、批量逐个上传、轮询方式、详情/下载 API 说明 |
| v4 | 2026-06-24 | 补充：uploaded_by/token_count/阈值/updated_at/chunks 分页、批量失败隔离 |

# B 端管理后台 + 知识库 RAG 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地独立 React Admin（:8081）、管理员 API、知识库上传/向量化/RAG 检索，以及仪表盘/用户/课程/订单/监控五个运营模块。

**Architecture:** Phase 0 建地基（role、pgvector、admin 脚手架）→ Phase 1 运营 CRUD → Phase 2 知识库 ingestion → Phase 3 AI `knowledge_search` + 监控 + 全链路验收。向量存 Postgres pgvector；原件存 MinIO；Embedding 用 DeepSeek HTTP API。

**Tech Stack:** React 18, Ant Design 5, Vite, TanStack Query, Zustand, FastAPI, SQLAlchemy, pgvector, pymupdf, python-docx, DeepSeek Embeddings

**Plan 修订:** v2 — 修正 `get_current_admin` 写法；课程无 DELETE；分块用 langchain-text-splitters；pgvector score 公式；AI 工具位置不强制排序

**设计文档:** [2026-06-24-admin-knowledge-base-design.md](../specs/2026-06-24-admin-knowledge-base-design.md)（v4）

**测试说明:** 仓库无 pytest/vitest 基础设施；各 Task 用手动 `curl` + 浏览器 + `pnpm type-check` 验证，不新增测试框架。

**下载 API 决策:** 一期采用 **MinIO 预签名 URL**（`presigned_get_object`，有效期 15 分钟）。

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `packages/config/index.ts` | Modify | 新增 `admin: 8081` |
| `packages/common/user/index.ts` | Modify | `UserRole`, login 响应含 `role` |
| `packages/common/admin/index.ts` | Create | Dashboard、AdminUser、AdminCourse 等类型 |
| `packages/common/knowledge/index.ts` | Create | `DocumentStatus`、KnowledgeSearchResult |
| `packages/common/package.json` | Modify | exports 新子路径 |
| `server/pyproject.toml` | Modify | pymupdf, python-docx, pgvector |
| `server/app/config.py` | Modify | embedding / knowledge 配置项 |
| `server/ai/config.py` | Modify | 同上（AI 读 embedding 配置） |
| `server/.env.example` | Modify | 新环境变量 |
| `server/app/models/user.py` | Modify | `role` |
| `server/app/models/course.py` | Modify | `is_published` |
| `server/app/models/knowledge.py` | Create | DocumentStatus, KnowledgeDocument, KnowledgeChunk |
| `server/app/models/__init__.py` | Modify | export knowledge models |
| `server/alembic/versions/*_admin_knowledge.py` | Create | pgvector + 新字段 + 知识库表 |
| `server/scripts/probe_embedding.py` | Create | Phase 0 实测 embedding 维度 |
| `server/app/dependencies.py` | Modify | `get_current_admin` |
| `server/app/services/user.py` | Modify | `user_to_response` 加 `role` |
| `server/app/services/course.py` | Modify | C 端 list 过滤 `is_published` |
| `server/app/services/knowledge/embedding.py` | Create | DeepSeek embed API |
| `server/app/services/knowledge/parser.py` | Create | txt/md/pdf/docx 解析 |
| `server/app/services/knowledge/ingest.py` | Create | 分块 + 向量化 + 状态机 |
| `server/app/services/knowledge/search.py` | Create | pgvector 检索 + 阈值过滤 |
| `server/app/services/knowledge/storage.py` | Create | MinIO 上传/删除/预签名 |
| `server/app/services/admin/dashboard.py` | Create | 仪表盘聚合 |
| `server/app/services/admin/users.py` | Create | 用户列表/详情 |
| `server/app/services/admin/courses.py` | Create | 课程 CRUD/上下架 |
| `server/app/services/admin/orders.py` | Create | 订单列表/详情 |
| `server/app/services/admin/analytics.py` | Create | PV/UV/错误/性能 |
| `server/app/routers/admin/__init__.py` | Create | 聚合 admin 路由 |
| `server/app/routers/admin/dashboard.py` | Create | |
| `server/app/routers/admin/users.py` | Create | |
| `server/app/routers/admin/courses.py` | Create | |
| `server/app/routers/admin/orders.py` | Create | |
| `server/app/routers/admin/knowledge.py` | Create | |
| `server/app/routers/admin/analytics.py` | Create | |
| `server/app/main.py` | Modify | `include_router(admin)` |
| `server/ai/services/tools/knowledge.py` | Create | `knowledge_search` 工具 |
| `server/ai/services/tools/__init__.py` | Modify | normal 角色挂载工具 |
| `server/seed.py` | Modify | 预置管理员账号 |
| `apps/admin/package.json` | Create | @en/admin |
| `apps/admin/vite.config.ts` | Create | proxy + port 8081 |
| `apps/admin/src/main.tsx` | Create | |
| `apps/admin/src/router/index.tsx` | Create | 路由 + 守卫 |
| `apps/admin/src/stores/user.ts` | Create | Zustand 登录态 |
| `apps/admin/src/apis/index.ts` | Create | Axios 实例 |
| `apps/admin/src/layout/AdminLayout.tsx` | Create | 侧栏布局 |
| `apps/admin/src/views/Login.tsx` | Create | |
| `apps/admin/src/views/Dashboard.tsx` | Create | |
| `apps/admin/src/views/users/*` | Create | List + Detail |
| `apps/admin/src/views/courses/*` | Create | List + Form |
| `apps/admin/src/views/orders/*` | Create | List + Detail |
| `apps/admin/src/views/analytics/Overview.tsx` | Create | 三 Tab |
| `apps/admin/src/views/knowledge/*` | Create | List + Search + Detail |
| `package.json` | Modify | `pnpm admin` 脚本 |

---

## Phase 0 — 地基（必须先完成）

> **完成标准:** pgvector 扩展已启用；管理员可登录 B 端空壳；非 admin 403；`EMBEDDING_DIMENSIONS` 已写入 `.env`。

---

### Task 0.1: Python 依赖与配置项

**Files:**
- Modify: `server/pyproject.toml`
- Modify: `server/app/config.py`
- Modify: `server/ai/config.py`
- Modify: `server/.env.example`

- [ ] **Step 1:** `pyproject.toml` dependencies 追加：

```toml
"pymupdf>=1.24.0",
"python-docx>=1.1.0",
"pgvector>=0.3.0",
"langchain-text-splitters>=0.3",
```

- [ ] **Step 2:** 在 `AppSettings`（`app/config.py`）追加：

```python
deepseek_embedding_model: str = Field(default="deepseek-embed", alias="DEEPSEEK_EMBEDDING_MODEL")
embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")
knowledge_max_file_size: int = Field(default=20971520, alias="KNOWLEDGE_MAX_FILE_SIZE")
knowledge_chunk_size: int = Field(default=500, alias="KNOWLEDGE_CHUNK_SIZE")
knowledge_chunk_overlap: int = Field(default=50, alias="KNOWLEDGE_CHUNK_OVERLAP")
knowledge_min_score: float = Field(default=0.5, alias="KNOWLEDGE_MIN_SCORE")
```

- [ ] **Step 3:** `ai/config.py` 的 `AISettings` 同步 embedding 相关字段（或直接从 `app.config.settings` 读取，与现有 DeepSeek key 一致）。

- [ ] **Step 4:** `.env.example` 追加设计文档中的 5 个 KNOWLEDGE_* / EMBEDDING_* 变量；`CORS_ORIGINS` 示例加入 `http://localhost:8081`。

- [ ] **Step 5:** 安装依赖

```bash
cd server && uv sync
```

预期：无依赖冲突。

---

### Task 0.2: Embedding 维度实测脚本

**Files:**
- Create: `server/scripts/probe_embedding.py`

- [ ] **Step 1:** 创建脚本：

```python
"""Phase 0: 实测 DeepSeek Embedding 返回维度。运行: cd server && uv run python scripts/probe_embedding.py"""
import asyncio
import httpx
from app.config import settings

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.deepseek.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={"model": settings.deepseek_embedding_model, "input": "hello"},
        )
        resp.raise_for_status()
        vec = resp.json()["data"][0]["embedding"]
        print(f"model={settings.deepseek_embedding_model}")
        print(f"dimensions={len(vec)}")
        print(f"Set EMBEDDING_DIMENSIONS={len(vec)} in server/.env")

asyncio.run(main())
```

- [ ] **Step 2:** 运行并更新 `.env`

```bash
cd server && uv run python scripts/probe_embedding.py
```

预期：打印实际维度；手动写入 `EMBEDDING_DIMENSIONS=<打印值>`。

---

### Task 0.3: 数据库迁移 — role、is_published、pgvector

**Files:**
- Modify: `server/app/models/user.py`
- Modify: `server/app/models/course.py`
- Create: `server/app/models/knowledge.py`（仅枚举 + 空模型占位，Task 2.1 完善）
- Modify: `server/app/models/__init__.py`
- Create: `server/alembic/versions/<rev>_admin_role_and_pgvector.py`

- [ ] **Step 1:** `User` 追加：

```python
role: Mapped[str] = mapped_column(String, default="user")  # user | admin
```

- [ ] **Step 2:** `Course` 追加：

```python
is_published: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 3:** 生成迁移（或手写）首步含：

```python
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
op.add_column("user", sa.Column("role", sa.String(), server_default="user", nullable=False))
op.add_column("course", sa.Column("is_published", sa.Boolean(), server_default=sa.true(), nullable=False))
```

- [ ] **Step 4:** 执行迁移

```bash
cd server && uv run alembic upgrade head
```

预期：`user.role`、`course.is_published` 存在；`\dx` 可见 vector 扩展。

---

### Task 0.4: 管理员鉴权 + 登录返回 role

**Files:**
- Modify: `server/app/dependencies.py`
- Modify: `server/app/services/user.py`
- Modify: `packages/common/user/index.ts`

- [ ] **Step 1:** `dependencies.py` 追加（**用 `Depends(get_current_user)` 组合，勿 `await get_current_user(...)`**）：

```python
async def get_current_admin(
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(select(User.role).where(User.id == payload["userId"]))
    role = result.scalar_one_or_none()
    if role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return payload
```

（需 `from app.database import get_db` 与 `AsyncSession`。）

- [ ] **Step 2:** `user_to_response` 追加 `"role": user.role`。

- [ ] **Step 3:** `packages/common/user/index.ts` 追加 `export type UserRole = 'user' | 'admin'`，Login 响应类型含 `role`。

- [ ] **Step 4:** 验证非 admin 403（Phase 0.8 路由挂载后执行）。

---

### Task 0.5: 种子管理员账号

**Files:**
- Modify: `server/seed.py`

- [ ] **Step 1:** 追加管理员常量（密码与现有用户一致：前端 MD5 后再 bcrypt，seed 里直接 bcrypt 存储）：

```python
ADMIN = {
    "phone": "13800000000",
    "name": "管理员",
    "password": "<bcrypt of md5('admin123')>",  # 实施时生成一次
    "role": "admin",
}
```

- [ ] **Step 2:** seed 逻辑：若 phone 不存在则 insert，若存在则 `UPDATE role='admin'`。

- [ ] **Step 3:** 运行

```bash
cd server && uv run python seed.py
```

预期：DB 中存在 `role=admin` 用户。

---

### Task 0.6: packages/config + admin 路由骨架

**Files:**
- Modify: `packages/config/index.ts`
- Create: `server/app/routers/admin/__init__.py`
- Create: `server/app/routers/admin/dashboard.py`
- Modify: `server/app/main.py`

- [ ] **Step 1:** `Config.ports.admin = 8081`。

- [ ] **Step 2:** `admin/__init__.py`：

```python
from fastapi import APIRouter
from . import dashboard

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
router.include_router(dashboard.router)

@router.get("/ping")
async def admin_ping():
    return {"data": {"ok": True}, "code": 200, "message": "pong"}
```

- [ ] **Step 3:** `dashboard.py` 暂留空 router 或仅 ping。

- [ ] **Step 4:** `main.py`：

```python
from app.routers.admin import router as admin_router
app.include_router(admin_router)
```

- [ ] **Step 5:** 验证（需 admin token）：

```bash
curl -H "Authorization: Bearer <admin_access_token>" http://localhost:3000/api/v1/admin/ping
```

预期：200；普通用户 token → 403。

---

### Task 0.7: apps/admin React 脚手架

**Files:**
- Create: `apps/admin/package.json`
- Create: `apps/admin/vite.config.ts`
- Create: `apps/admin/tsconfig.json`
- Create: `apps/admin/index.html`
- Create: `apps/admin/src/main.tsx`
- Create: `apps/admin/src/App.tsx`
- Create: `apps/admin/src/router/index.tsx`
- Create: `apps/admin/src/stores/user.ts`
- Create: `apps/admin/src/apis/index.ts`
- Create: `apps/admin/src/layout/AdminLayout.tsx`
- Create: `apps/admin/src/views/Login.tsx`
- Modify: `package.json`（根）
- Modify: `pnpm-workspace.yaml`（已含 `apps/*`，无需改）

- [ ] **Step 1:** `package.json`（@en/admin）核心依赖：

```json
{
  "name": "@en/admin",
  "private": true,
  "type": "module",
  "scripts": { "dev": "vite", "build": "tsc -b && vite build", "preview": "vite preview" },
  "dependencies": {
    "@ant-design/icons": "^5.6.1",
    "@en/common": "workspace:*",
    "@en/config": "workspace:*",
    "@tanstack/react-query": "^5.62.0",
    "antd": "^5.22.0",
    "axios": "^1.13.2",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "~5.3.0",
    "vite": "^5.0.10"
  }
}
```

- [ ] **Step 2:** `vite.config.ts` 参照 web，port 用 `Config.ports.admin`，proxy `/api` → 3000。

- [ ] **Step 3:** `apis/index.ts` — Axios `baseURL: '/api/v1'`，请求拦截器带 Bearer，401 跳登录。

- [ ] **Step 4:** `stores/user.ts` — 存 `accessToken`、`user`（含 `role`），persist localStorage。

- [ ] **Step 5:** `Login.tsx` — 调 `POST /user/login`（phone+password，password 前端 md5 与 C 端一致）；`role !== 'admin'` 则 `message.error('无管理员权限')`。

- [ ] **Step 6:** `AdminLayout.tsx` — Ant Design `Layout` + 侧栏菜单（占位项）；顶栏显示用户名 + 退出。

- [ ] **Step 7:** 根 `package.json` 加 `"admin": "pnpm --filter @en/admin dev"`。

- [ ] **Step 8:** 安装并启动

```bash
pnpm install
pnpm admin
```

预期：`http://localhost:8081/login` 可打开；管理员登录后进入空壳 Layout。

---

## Phase 1 — 运营模块

> **完成标准:** 仪表盘/用户/课程/订单四个模块 API + 前端可用；C 端课程列表隐藏下架课。

---

### Task 1.1: 仪表盘 API

**Files:**
- Create: `server/app/services/admin/dashboard.py`
- Modify: `server/app/routers/admin/dashboard.py`

- [ ] **Step 1:** `get_dashboard_stats(db)` 聚合 spec 中 11 个字段（`today*` 用 UTC 日界或本地日界，与现有 dashboard 一致）。

- [ ] **Step 2:** `GET /admin/dashboard` + `Depends(get_current_admin)`。

- [ ] **Step 3:** curl 验证返回数值与 SQL 手工查询一致。

---

### Task 1.2: 用户管理 API

**Files:**
- Create: `server/app/services/admin/users.py`
- Create: `server/app/routers/admin/users.py`
- Modify: `server/app/routers/admin/__init__.py`

- [ ] **Step 1:** 列表：分页 + `keyword` ILIKE `name/phone/email`；返回 `{ list, total }`。

- [ ] **Step 2:** 详情：用户基本信息 + `masteredWords`（WordBookRecord is_master count）+ `purchasedCourses`（CourseRecord is_purchased）+ `recentCourses` 简要列表。

- [ ] **Step 3:** 挂载路由 `GET /users`、`GET /users/{id}`。

---

### Task 1.3: 课程管理 API + C 端过滤

**Files:**
- Create: `server/app/services/admin/courses.py`
- Create: `server/app/routers/admin/courses.py`
- Modify: `server/app/services/course.py`
- Modify: `packages/common/admin/index.ts`

- [ ] **Step 1:** `get_course_list` 加 `.where(Course.is_published.is_(True))`（**仅 C 端 list**；admin list 不过滤）。

- [ ] **Step 2:** Admin CRUD：`POST/PUT` body 校验；`PUT .../publish|unpublish` 改 `is_published`。**不提供 `DELETE /courses/{id}`**（与 spec 一致：仅软下架，禁止硬删）。

- [ ] **Step 3:** 新建课程用 `nanoid` 生成 id，与 seed 一致。

- [ ] **Step 4:** 验证：下架课后 C 端 `/api/v1/course/list` 不可见，已购用户 `/course/my` 仍可见。

---

### Task 1.4: 订单管理 API

**Files:**
- Create: `server/app/services/admin/orders.py`
- Create: `server/app/routers/admin/orders.py`

- [ ] **Step 1:** 列表：join User；筛选 `trade_status`、`created_at` 日期范围；`keyword` 匹配 `out_trade_no` 或用户名。

- [ ] **Step 2:** 详情：PaymentRecord + 关联 CourseRecord/Course。

- [ ] **Step 3:** 挂载路由。

---

### Task 1.5: Admin 前端 — 仪表盘 + 用户 + 课程 + 订单

**Files:**
- Create: `apps/admin/src/apis/admin.ts`
- Create: `apps/admin/src/views/Dashboard.tsx`
- Create: `apps/admin/src/views/users/List.tsx`, `Detail.tsx`
- Create: `apps/admin/src/views/courses/List.tsx`, `Form.tsx`
- Create: `apps/admin/src/views/orders/List.tsx`, `Detail.tsx`
- Modify: `apps/admin/src/router/index.tsx`

- [ ] **Step 1:** `admin.ts` 封装四个模块 API，TanStack Query hooks。

- [ ] **Step 2:** `Dashboard.tsx` — 4 Statistic 卡片 + 2 折线图（可用 `@ant-design/plots` 或 ECharts）。

- [ ] **Step 3:** 用户/订单 — `Table` + 分页 + 搜索；详情页 `Descriptions`。

- [ ] **Step 4:** 课程 — 列表含上架状态 Tag；Form 新建/编辑；上下架按钮调 publish/unpublish。

- [ ] **Step 5:** 路由注册 + 侧栏菜单（知识库占位 disabled 或链到空页）。

- [ ] **Step 6:** 浏览器走查四个模块。

---

## Phase 2 — 知识库

> **完成标准:** 可上传 txt/md/pdf/docx 至 ready；列表/详情/检索测试页可用。

---

### Task 2.1: 知识库模型与迁移

**Files:**
- Modify: `server/app/models/knowledge.py`
- Modify: `server/app/models/__init__.py`
- Create: `server/alembic/versions/<rev>_knowledge_tables.py`

- [ ] **Step 1:** 完整模型（spec v4）：

```python
class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_document"
    # 全部字段见 spec；status 用 SAEnum(DocumentStatus)
    uploaded_by: Mapped[str] = mapped_column(String(30), ForeignKey("user.id"), nullable=False)

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunk"
    embedding: Mapped[list] = mapped_column(Vector(settings.embedding_dimensions))  # pgvector
```

- [ ] **Step 2:** 迁移创建 HNSW 索引：

```sql
CREATE INDEX idx_knowledge_chunk_embedding ON knowledge_chunk
  USING hnsw (embedding vector_cosine_ops);
```

- [ ] **Step 3:** `alembic upgrade head`。

---

### Task 2.2: MinIO 存储封装

**Files:**
- Create: `server/app/services/knowledge/storage.py`

- [ ] **Step 1:** 实现：

```python
async def upload_bytes(key: str, data: bytes, content_type: str) -> None: ...
async def download_bytes(key: str) -> bytes: ...
async def delete_object(key: str) -> None: ...  # 失败只 log warning
async def presigned_download_url(key: str, expires: int = 900) -> str: ...
def make_key(document_id: str, filename: str) -> str:
    return f"knowledge/{document_id}/{filename}"
```

- [ ] **Step 2:** 复用 `shared/minio_client.py` 的 bucket（与头像同 bucket，不同前缀）。

---

### Task 2.3: 文档解析

**Files:**
- Create: `server/app/services/knowledge/parser.py`

- [ ] **Step 1:** 扩展名 + MIME 白名单校验函数 `validate_upload(filename, content_type) -> None | raise ValueError`。

- [ ] **Step 2:** 解析器：

```python
def parse_document(filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".txt", ".md"):
        return raw.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        import fitz  # pymupdf
        doc = fitz.open(stream=raw, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    if ext == ".docx":
        from docx import Document
        doc = Document(BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    raise ValueError("不支持的文件格式")
```

---

### Task 2.4: Embedding 客户端

**Files:**
- Create: `server/app/services/knowledge/embedding.py`

- [ ] **Step 1:**

```python
async def embed_texts(texts: list[str]) -> list[list[float]]:
    # POST https://api.deepseek.com/v1/embeddings
    # 批量请求；返回 vectors
    for vec in vectors:
        if len(vec) != settings.embedding_dimensions:
            raise ValueError("Embedding 维度不匹配")
    return vectors

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)
```

---

### Task 2.5: Ingestion 流水线

**Files:**
- Create: `server/app/services/knowledge/ingest.py`

- [ ] **Step 1:** `async def run_ingestion(document_id: str) -> None` 完整状态机（spec 处理流程 + reindex 删旧 chunk）。

- [ ] **Step 2:** 分块用 **`langchain-text-splitters`** 的 `RecursiveCharacterTextSplitter`（`pyproject.toml` 追加 `"langchain-text-splitters>=0.3"`）；`chunk_size` / `chunk_overlap` 读配置。**不要手写切分。**

- [ ] **Step 3:** 空文本 → `failed`, `"文档内容为空"`。

- [ ] **Step 4:** 维度不匹配 → `failed`, `"Embedding 维度不匹配"`。

- [ ] **Step 5:** 通用异常 → `failed`, `str(e)[:500]`，清理 partial chunks。

- [ ] **Step 6:** `async def assert_processing_capacity(db)` — processing count >= 3 抛 HTTP 429（供 router 调用）。

---

### Task 2.6: 向量检索

**Files:**
- Create: `server/app/services/knowledge/search.py`
- Modify: `packages/common/knowledge/index.ts`

- [ ] **Step 1:**

```python
async def search_knowledge(db, query: str, top_k: int = 5) -> dict:
    query_vec = (await embed_texts([query]))[0]
    # pgvector: `<=>` 为 cosine distance（0=最相似，2=最不相似）
    # cosine_similarity = 1 - distance  →  score = 1 - (embedding <=> query_vec)
    # 过滤 score >= settings.knowledge_min_score
    return {"results": [...], "query": query, "totalTokens": sum(estimate_tokens(r["content"]) for r in results)}
```

- [ ] **Step 2:** TypeScript 类型与 spec JSON 对齐。

---

### Task 2.7: 知识库 Admin API

**Files:**
- Create: `server/app/routers/admin/knowledge.py`
- Modify: `server/app/routers/admin/__init__.py`

- [ ] **Step 1:** `POST /upload` — 校验大小/格式 → MinIO → DB pending → `BackgroundTasks.add_task(run_ingestion, id)`；返回 `{ id, status: "pending" }`。

- [ ] **Step 2:** `GET /` — 分页/keyword/status/created_at DESC。

- [ ] **Step 3:** `GET /{id}` — 详情字段：

```json
{
  "id", "title", "filename", "mimeType", "fileSize", "status",
  "chunkCount", "errorMessage", "uploadedBy", "createdAt", "updatedAt"
}
```

- [ ] **Step 4:** `GET /{id}/chunks?page&pageSize` — `{ list: [{ chunkIndex, content, tokenCount }], total }`。

- [ ] **Step 5:** `PUT /{id}` — 改 title；`DELETE /{id}` — DB 再 MinIO；`POST /{id}/reindex`；`GET /search?q&topK`；`GET /{id}/download` — 返回 `{ url: presigned }`。

- [ ] **Step 6:** curl 上传 sample txt，轮询至 ready，调用 search 有结果。

---

### Task 2.8: Admin 前端 — 知识库

**Files:**
- Create: `apps/admin/src/views/knowledge/List.tsx`
- Create: `apps/admin/src/views/knowledge/Detail.tsx`
- Create: `apps/admin/src/views/knowledge/Search.tsx`
- Modify: `apps/admin/src/router/index.tsx`
- Modify: `apps/admin/src/layout/AdminLayout.tsx`

- [ ] **Step 1:** `List.tsx` — Dragger 多文件；**逐个** `POST /upload`；单文件失败 `message.error` 不阻断队列；processing 时 `refetchInterval: 3000`。

- [ ] **Step 2:** 表格列：title、filename、status Tag、chunkCount、createdAt；操作 reindex/delete/详情。

- [ ] **Step 3:** `Detail.tsx` — 元信息 + 分页 chunks Table。

- [ ] **Step 4:** `Search.tsx` — 输入 q + topK，卡片展示 score/title/content。

- [ ] **Step 5:** 侧栏「知识库」第二位启用。

---

## Phase 3 — AI 闭环 + 监控

> **完成标准:** normal 角色 RAG 可用；监控三 Tab 有数据；spec 验收清单全绿。

---

### Task 3.1: AI knowledge_search 工具

**Files:**
- Create: `server/ai/services/tools/knowledge.py`
- Modify: `server/ai/services/tools/__init__.py`

- [ ] **Step 1:** 工具实现：

```python
@tool
async def knowledge_search(query: str) -> str:
    """从平台知识库检索与学习相关的内部资料。..."""
    from app.database import async_session
    from app.services.knowledge.search import search_knowledge
    async with async_session() as db:
        result = await search_knowledge(db, query, top_k=5)
    # 截断总字符 <= 3000
    return json.dumps(result, ensure_ascii=False)
```

- [ ] **Step 2:** `make_tools` 列表 **append `knowledge_search`**（与其他工具并列，**不强制** word_lookup/web_search 前后顺序；推荐放在 `course_purchase` 之后）。

- [ ] **Step 3:** C 端 normal 聊天提问知识库内内容，观察 tool call 与回答。

---

### Task 3.2: 数据监控 API

**Files:**
- Create: `server/app/services/admin/analytics.py`
- Create: `server/app/routers/admin/analytics.py`

- [ ] **Step 1:** `overview` — 按天聚合 PV（page_view）、UV（distinct visitor_id）；参数 `days=7|30`。

- [ ] **Step 2:** `pages` — `GROUP BY path ORDER BY count DESC LIMIT 20`。

- [ ] **Step 3:** `errors` — 分页 ErrorEntry，含 stack。

- [ ] **Step 4:** `performance` — avg(fp,fcp,lcp,inp,cls) + 可选按日趋势。

---

### Task 3.3: Admin 前端 — 监控 + 收尾

**Files:**
- Create: `apps/admin/src/views/analytics/Overview.tsx`
- Modify: `package.json`（根，`pnpm all` 可选加 admin）

- [ ] **Step 1:** `Overview.tsx` — Tabs：流量（折线+柱状）、错误（Table expandable）、性能（Statistic 卡片）。

- [ ] **Step 2:** 根脚本可选：`"all": "concurrently \"pnpm run web\" \"pnpm run admin\" \"pnpm run server\" \"pnpm run ai\""`。

- [ ] **Step 3:** 更新 spec 头部状态为「已有实现计划」。

---

### Task 3.4: 全链路冒烟清单

- [ ] 管理员登录 B 端；普通用户拒绝
- [ ] 上传 `test.md` → ready → 检索测试 score ≥ 0.5
- [ ] C 端 normal 问文档内问题，AI 回答正确
- [ ] 问单词释义仍触发 word_lookup（观察 SSE tool 事件）
- [ ] 课程下架后 C 端 list 不可见
- [ ] 仪表盘数字与 DB 一致
- [ ] 非 admin 调 `/api/v1/admin/*` → 403

---

## Spec 覆盖自检

| Spec 章节 | 对应 Task |
|-----------|-----------|
| 认证 role + get_current_admin | 0.3, 0.4 |
| Course is_published + C 端过滤 | 0.3, 1.3 |
| 知识库表 + pgvector HNSW | 0.1, 2.1 |
| ingestion 状态机/并发/失败 | 2.5, 2.7 |
| 检索格式 + MIN_SCORE | 2.6, 3.1 |
| Admin 全部 API | 1.1–1.4, 2.7, 3.2 |
| React Admin 全部页面 | 0.7, 1.5, 2.8, 3.3 |
| AI knowledge_search | 3.1 |
| 环境变量/依赖 | 0.1, 0.2 |
| 种子管理员 | 0.5 |
| 验收标准 | 3.4 |

无遗漏项。

---

## 建议 Commit 粒度

| Commit | 范围 |
|--------|------|
| 1 | Phase 0 后端：deps, migration, admin auth, seed |
| 2 | Phase 0 前端：apps/admin 脚手架 + login |
| 3 | Phase 1：运营 API + 前端四页 |
| 4 | Phase 2：knowledge 后端全流程 |
| 5 | Phase 2：knowledge 前端 |
| 6 | Phase 3：AI tool + analytics + 收尾 |

---

**Plan 完成。** 保存路径：`docs/superpowers/plans/2026-06-24-admin-knowledge-base.md`

**两种执行方式：**

1. **Subagent-Driven（推荐）** — 每个 Task 派生子 agent，Task 间人工 review，迭代快
2. **Inline Execution** — 本会话按 Phase 顺序直接实现，Phase 末 checkpoint 验收

你想用哪种方式开始 Phase 0？

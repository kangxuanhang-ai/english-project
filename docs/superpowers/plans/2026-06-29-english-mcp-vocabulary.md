# 生词本 + English MCP Server 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付 Web 生词本（Phase 0）、Claude Code CLI stdio MCP 三阶段（查词/语法/进度 → 知识库/课程 → 生词本 MCP），共用 `app/services/` 业务层。

**Architecture:** 先从 LangChain tool 抽出纯 async services；Web `my-words` API 与 MCP 均调同一 services；MCP 独立进程 + `english_mcp/db.py` 自建 SQLAlchemy engine；FastMCP stdio；**本地包名 `english_mcp`（不可用 `mcp`，会与官方 SDK 冲突）**。

**Tech Stack:** FastAPI, SQLAlchemy async, Vue 3, `@en/common`, Python `mcp` (FastMCP), Claude Code CLI

**Spec:** `docs/superpowers/specs/2026-06-29-english-mcp-vocabulary-design.md`

---

## 文件总览

| 阶段 | 新建 | 修改 |
|------|------|------|
| P0 生词本 | `app/services/my_words.py`, `app/routers/my_words.py`, `app/schemas/my_words.py`, `apps/web/src/views/MyWords/index.vue`, `apps/web/src/apis/my-words/` | `learn.py`, `main.py`, `router`, `WordBook/index.vue`, `packages/common/word/` |
| P0 抽 service | `app/services/word_lookup.py`, `grammar_check.py`, `progress_snapshot.py` | `ai/services/tools/word.py`, `grammar.py`, `progress.py`, `user_context.py` |
| P1 MCP | `server/english_mcp/**`, `scripts/smoke_mcp_tools.py` | `pyproject.toml`, `.env.example`, `.mcp.json`（追加 english，保留 pencil）, hatch 增加 `english_mcp` |
| P2 MCP | `english_mcp/tools/knowledge.py`, `courses.py`, `recommend.py`, `english_mcp/resources/` | `app/services/knowledge_search_service.py` 等 |
| P3 MCP | `english_mcp/tools/my_words.py` | 可选 `english_mcp/http_server.py` |

---

# Phase 0 — 生词本 + 共享 Services

### Task 0.1: 共享查词 service

**Files:**
- Create: `server/app/services/word_lookup.py`
- Modify: `server/ai/services/tools/word.py`

- [ ] **Step 1: 创建 `lookup_words(db, words: list[str]) -> list[dict]`**

从 `word.py` 抽出 SQL 与结果组装，返回 list[dict]（非 JSON 字符串）。

- [ ] **Step 2: 改 LangChain tool 为薄 wrapper**

```python
async def word_lookup(words: list[str]) -> str:
    async with async_session() as session:
        results = await lookup_words(session, words)
    return json.dumps(results, ensure_ascii=False)
```

- [ ] **Step 3: 冒烟**

```bash
cd server && uv run python -c "
import asyncio
from app.database import async_session
from app.services.word_lookup import lookup_words
async def main():
    async with async_session() as db:
        print(await lookup_words(db, ['abandon']))
asyncio.run(main())
"
```

Expected: 打印含 word/translation 的 dict 列表。

---

### Task 0.2: 共享语法 service

**Files:**
- Create: `server/app/services/grammar_check.py`
- Modify: `server/ai/services/tools/grammar.py`

- [ ] **Step 1: 创建 `async def check_grammar(text: str) -> str`**

移入 `GRAMMAR_PROMPT`、长度校验、LLM 调用；**不含 user_id、不含限流**。

- [ ] **Step 2: `make_grammar_check` 保留 `_allow_grammar(user_id)` 在 tool 层**

- [ ] **Step 3: 验证 Web 聊天 grammar 仍可用**（手动或现有 smoke）

---

### Task 0.3: 共享进度 service

**Files:**
- Create: `server/app/services/progress_snapshot.py`
- Modify: `server/ai/services/user_context.py`, `server/ai/services/tools/progress.py`

- [ ] **Step 1: `fetch_user_progress_json(db, user_id)` 移入 progress_snapshot**

`user_context.py` 改为调用该函数（注入 session 或内部开 session，与现行为一致）。

- [ ] **Step 2: progress tool 薄 wrapper 不变对外行为**

---

### Task 0.4: 生词本 service

**Files:**
- Create: `server/app/services/my_words.py`
- Modify: `server/app/services/learn.py`

- [ ] **Step 1: 实现 `list_my_words`**

```python
async def list_my_words(
    db: AsyncSession, user_id: str, status: str, page: int, page_size: int
) -> dict:
    # status: "learning" -> is_master False; "mastered" -> True
    # join WordBook, paginate, return { list, total }
```

- [ ] **Step 2: 实现 `add_words`**

按 word 字符串查 `WordBook`；创建 `WordBookRecord(is_master=False)`；已掌握则 skip 并收集 messages。

- [ ] **Step 3: 实现 `mark_mastered`**

支持 `word_ids` 或 `words`。三种情况：

1. 无记录 → 新建 `is_master=True`，`word_number += 1`
2. 已有 `is_master=False` → 更新为 `True`，`word_number += 1`（生词转掌握，只计一次）
3. 已有 `is_master=True` → 幂等 skip，**不**递增 `word_number`

- [ ] **Step 4: 实现 `remove_word`**

仅允许删除 `is_master=False` 记录。

- [ ] **Step 5: 重构 `learn.save_word_master`**

```python
async def save_word_master(db, word_ids, user_id):
    return await mark_mastered(db, user_id, word_ids=word_ids)
```

- [ ] **Step 6: 课程学词回归冒烟（commit 前必做）**

`save_word_master` 不涉及 `CourseRecord` 写操作，但须确认 `word_number` 与现有行为一致：

1. 已购课用户调用 `GET /api/v1/learn/word/{course_id}` 拿到 wordIds
2. `POST /api/v1/learn/word/master` 提交这批 wordIds
3. 断言：`wordNumber` 正确递增；重复提交同一批 **不** 重复计数
4. （可选）生词本中 `is_master=false` 的词经课程 master 后变为已掌握且只计一次

手动浏览器验收或临时脚本均可；**通过后再进入 Task 0.7 commit**。

---

### Task 0.5: 生词本 API + Schema

**Files:**
- Create: `server/app/schemas/my_words.py`, `server/app/routers/my_words.py`
- Modify: `server/app/main.py`

- [ ] **Step 1: Pydantic schemas**

`AddWordsDto`, `MarkMasteredDto`, `MyWordItem`, `MyWordListResponse`

- [ ] **Step 2: Router 四个端点**（见 spec §3.1；router prefix=`/api/v1/my-words`，相对路径 `""`, `"/master"`, `"/{wordId}"`）

- [ ] **Step 3: `app.include_router(my_words.router)`**

- [ ] **Step 4: curl 冒烟**

```bash
# 需有效 JWT
curl -H "Authorization: Bearer $TOKEN" "http://localhost:3000/api/v1/my-words?status=learning"
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"words":["abandon"]}' http://localhost:3000/api/v1/my-words
```

---

### Task 0.6: 前端生词本

**Files:**
- Create: `packages/common/word/my-words.ts`（或扩展现有 `word/index.ts`）
- Create: `apps/web/src/apis/my-words/index.ts`
- Create: `apps/web/src/views/MyWords/index.vue`
- Modify: `apps/web/src/router/index.ts`, 新建 `apps/web/src/router/my-words/index.ts`, `apps/web/src/views/WordBook/index.vue`, 导航组件

- [ ] **Step 1: 类型 + API 模块**

- [ ] **Step 2: MyWords 页 — Tab 复习中/已掌握、分页、标记掌握、删除**

- [ ] **Step 3: 路由 `router/my-words/index.ts`** — `path: '/my-words'`, `meta: { requiresAuth: true }`，并在 `router/index.ts` 注册

- [ ] **Step 4: 词库卡片「加入生词本」调用 POST `/my-words`**

- [ ] **Step 5: `pnpm --filter @en/web type-check`**

- [ ] **Step 6: `pnpm --filter @en/web build`**

Expected: 0 error（与 QA-01 一致；新页面/路由须能通过生产构建）

---

### Task 0.7: Phase 0 提交

- [ ] **Commit**

```bash
git add server/app/services/my_words.py server/app/routers/my_words.py ...
git commit -m "feat: add my vocabulary notebook API and web UI with shared word services"
```

---

# Phase 1 — MCP 基础（stdio + 3 tools）

### Task 1.1: 依赖与包结构

**Files:**
- Modify: `server/pyproject.toml`, `[tool.hatch.build.targets.wheel] packages`
- Create: `server/english_mcp/__init__.py`, `__main__.py`

- [ ] **Step 1: 添加 MCP Python SDK 依赖**

PyPI 包名为 `mcp`（官方 MCP SDK，含 FastMCP）；**不写死版本号**，由 uv 解析最新兼容版本并写入 lockfile。**本地业务包命名为 `english_mcp`**，不可命名为 `mcp`（会与 `from mcp.server.fastmcp import FastMCP` 冲突）：

```bash
cd server && uv add mcp
```

- [ ] **Step 2: hatch packages 增加 `english_mcp`**（不是 `mcp`）

- [ ] **Step 3: `__main__.py` 调用 `english_mcp.server` 的 main/run**

---

### Task 1.2: MCP config + db + auth

**Files:**
- Create: `server/english_mcp/config.py`, `db.py`, `auth.py`, `rate_limit.py`

- [ ] **Step 1: `MCPSettings`** — 读 `DATABASE_URL`, `DEEPSEEK_*`, `ENGLISH_MCP_*`, pool size

- [ ] **Step 2: `init_db` / `dispose_db`**（spec §2.2，pool_size=5）

- [ ] **Step 3: `resolve_user_id()`** — Key 匹配 → user_id；否则 demo user；无 demo 且需 auth 的 tool 返回明确错误

- [ ] **Step 4: `rate_limit.py`** — `allow_grammar(key: str) -> bool`，15/min

---

### Task 1.3: FastMCP server + 三 tool

**Files:**
- Create: `server/english_mcp/server.py`, `server/english_mcp/tools/lookup_words.py`, `grammar.py`, `progress.py`

- [ ] **Step 1: lifespan 注册 init_db / dispose_db**

- [ ] **Step 2: 注册 `lookup_words`** — schema 为 `words: list[str]`（Claude 主路径会传 `["abandon"]`）；handler 内加防御性 `str → [str]` 兜底（见 spec §4.2），再调 `word_lookup` service + mcp db session

- [ ] **Step 3: 注册 `check_grammar`** — rate limit + `grammar_check` service

- [ ] **Step 4: 注册 `get_learning_progress`** — auth + `progress_snapshot`

- [ ] **Step 5: Windows — 若需则 `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())` 在 `__main__`**

---

### Task 1.4: 配置与冒烟

**Files:**
- Modify: `server/.env.example`, `.mcp.json`
- Create: `server/scripts/smoke_mcp_tools.py`（现有 `server/scripts/` 目录，与 eval 脚本同级）

- [ ] **Step 1: 更新 `.env.example`**

- [ ] **Step 2: `.mcp.json` 追加 english entry**（勿删除现有 `pencil`）

- [ ] **Step 3: smoke 脚本直接测三 tool handler**

```bash
cd server && uv run python scripts/smoke_mcp_tools.py
```

- [ ] **Step 4: 本机 Claude CLI**

```bash
claude mcp add --scope project english --env ENGLISH_MCP_API_KEY=... -- \
  uv run --directory server python -m english_mcp
claude mcp list
```

- [ ] **Step 5: Commit `feat(mcp): add stdio MCP server with lookup, grammar, progress tools`**

---

# Phase 2 — MCP 知识库 + 课程

### Task 2.1: 共享 course / knowledge services

**Files:**
- Create: `server/app/services/course_catalog.py`, `course_recommend_readonly.py`
- Create: `server/app/services/knowledge_search_service.py`（薄封装现有 `search_knowledge`）

- [ ] **Step 1: `list_published_courses(db) -> list[dict]`**

- [ ] **Step 2: `recommend_for_user(db, user_id, count, ...) -> dict`** — 复用 `ai/services/recommendation.py` 只读部分

- [ ] **Step 3: `search_knowledge_for_query(db, query) -> dict`**

---

### Task 2.2: MCP tools + resources

**Files:**
- Create: `server/english_mcp/tools/knowledge.py`, `courses.py`, `recommend.py`, `server/english_mcp/resources.py`

- [ ] **Step 1: 注册 `search_knowledge`, `list_courses`, `recommend_courses`**

- [ ] **Step 2: Resources `english://courses/catalog`, `english://user/progress`**

- [ ] **Step 3: 扩展 `smoke_mcp_tools.py`**

- [ ] **Step 4: Commit `feat(mcp): add knowledge search and course tools with resources`**

---

# Phase 3 — 生词本 MCP + 可选 HTTP

### Task 3.1: MCP 生词本 tools

**Files:**
- Create: `server/english_mcp/tools/my_words.py`

- [ ] **Step 1: `list_my_words`** — status param，需 auth

- [ ] **Step 2: `add_words_to_review`** — 调 `my_words.add_words`

- [ ] **Step 3: `mark_words_mastered`**

- [ ] **Step 4: smoke + 与 Web API 结果对比**

- [ ] **Step 5: Commit `feat(mcp): expose vocabulary notebook tools`**

---

### Task 3.2（可选）: HTTP transport + platform_health

**Files:**
- Create: `server/english_mcp/http_server.py`, `server/english_mcp/tools/health.py`

- [ ] **Step 1: Streamable HTTP on port 3002**

- [ ] **Step 2: `platform_health` tool**

- [ ] **Step 3: 文档写入 spec 验收节**

---

# 答辩 Demo 脚本（Phase 0 + 1 完成后）

1. Web：词库页加入生词 → 「我的生词本」可见 → 标记掌握  
2. Claude CLI：`lookup_words abandon`  
3. Claude CLI：语法检查例句  
4. Claude CLI：学习进度（配 Key 或 demo user）  
5. （P2+）知识库 / 推荐；（P3）MCP 加词到生词本  

---

## Plan Self-Review

| Spec 章节 | 对应 Task |
|-----------|-----------|
| Phase 0 API | 0.4–0.6 |
| 业务层复用 | 0.1–0.3 |
| MCP P1 三 tool | 1.1–1.4 |
| MCP P2 | 2.1–2.2 |
| MCP P3 生词本 | 3.1 |
| HTTP 可选 | 3.2 |
| 鉴权 / db.py | 1.2 |

无 TBD；测试以 smoke 脚本 + 手动 Claude CLI 为主（项目无 pytest 基础设施）。

---

**Plan complete.** 建议执行顺序：Phase 0 → 1 → 2 → 3，每阶段验收后再进下一阶段。

**执行方式：**

1. **Subagent-Driven** — 每 Task 派生子 agent，任务间 review  
2. **Inline Execution** — 本会话按 Task 连续实现，阶段 checkpoint  

请选择执行方式，或指定「先从 Phase 0 开始」。

---

## 计划修订记录

| 日期 | 修订 |
|------|------|
| 2026-06-29 | 初稿 |
| 2026-06-29 | 审查修订：Task 0.4 `mark_mastered` 三态 + 课程学词回归 Step 6；Task 0.6 增加 build；Task 1.1 `uv add mcp` 不 pin 版本；Task 1.3 lookup str 归一化 |
| 2026-06-29 | 澄清：lookup 主路径为 list，str 归一化为防御性兜底 |
| 2026-06-29 | 自查：`english_mcp` 包名；API 路径；requiresAuth；`.mcp.json` 追加 pencil |

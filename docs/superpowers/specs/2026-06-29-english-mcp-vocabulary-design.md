# 生词本 + English MCP Server 设计

**日期**: 2026-06-29  
**状态**: 已批准（用户确认实现全部阶段）  
**范围**: Web 生词本、共享业务层抽取、Claude Code CLI stdio MCP（Phase 0 + MCP 三阶段）

---

## 1. 背景与动机

### 1.1 现状

| 能力 | 状态 |
|------|------|
| ECDICT 词库 `WordBook` + 前端「词库列表」 | ✅ 有（全站词典浏览，非个人笔记本） |
| 课程内学词 + `POST /learn/word/master` | ✅ 有（仅 `is_master=True`） |
| `WordBookRecord.is_master=False`（复习中/生词） | ❌  schema 有字段，业务未使用 |
| 独立「我的生词本」页面与 API | ❌ 无 |
| MCP Server 对外暴露平台能力 | ❌ 无 |

用户目标：

1. **答辩 + 学员**：Claude Code CLI 通过 stdio MCP 查词、语法、进度（及后续能力）
2. **产品闭环**：Web 端「我的生词本」，与 MCP 单词本 tool 共用业务层
3. **分阶段交付**：Phase 0 生词本 → MCP P1 → MCP P2 → MCP P3

### 1.2 命名约定

| 术语 | 含义 |
|------|------|
| **词库** | 表 `word_book`，ECDICT 全站词典 |
| **学习记录** | 表 `word_book_record`，用户 ↔ 单词 |
| **生词本** | `is_master=False` 的记录 + 专用 UI/API |
| **已掌握** | `is_master=True`（与现有 learn 流程一致） |

---

## 2. 方案选择

### 2.1 MCP 传输与客户端

| 选项 | 结论 |
|------|------|
| stdio + Claude Code CLI | **Phase 1～3 均采用**（答辩本机 demo） |
| Streamable HTTP + FRP | **Phase 3 可选**，文档预留，非答辩阻塞项 |

### 2.2 业务层复用（必须，非可选）

```
app/services/           ← 纯 async 业务，无 LangChain / FastMCP
  word_lookup.py
  grammar_check.py
  progress_snapshot.py   ← 与 plan 一致（非 progress.py）
  my_words.py
  knowledge_search_service.py
  course_catalog.py
  course_recommend_readonly.py

ai/services/tools/      ← LangChain @tool 薄 wrapper
english_mcp/tools/      ← FastMCP 薄 wrapper（包名见 §4.1）
```

**审查结论（mimo）**：MCP 独立进程不能「共享主进程 engine 实例」；`english_mcp/db.py` 自建 engine（同 DATABASE_URL，独立 pool，lifespan dispose）。

**包名约束（自查）**：本地 Python 包 **不得** 命名为 `mcp`——会与 PyPI 官方 SDK（`from mcp.server.fastmcp import FastMCP`）冲突。本地包统一用 **`english_mcp`**，启动命令 `python -m english_mcp`。

**打包**：`server/pyproject.toml` 的 `[tool.hatch.build.targets.wheel] packages` 现为 `app`, `ai`, `shared`；Phase 1 增加 **`english_mcp`**（与 plan Task 1.1 Step 2 一致）。

### 2.3 鉴权

| 场景 | 方式 |
|------|------|
| Web 生词本 | 现有 JWT（`get_current_user`） |
| MCP 个性化（进度、生词本） | `.env` 中 `ENGLISH_MCP_API_KEY` 与 `ENGLISH_MCP_USER_ID` 配对（单 Key 单用户；Phase 1 非多 Key 数据库） |
| MCP 无 Key | `ENGLISH_MCP_DEMO_USER_ID` fallback（答辩 demo） |
| MCP 公开 tool | `lookup_words`、`check_grammar` 无需 Key；语法限流在 MCP 层 |

Phase 1 不建 Admin 发 Key UI；手动配置 `.env`。

---

## 3. Phase 0 — Web 生词本

### 3.1 API（`server/app/routers/my_words.py`）

前缀：`/api/v1/my-words`（router prefix），均需登录。路径为 prefix 之后的相对路径（与现有 `word-book` 路由风格一致）：

| 方法 | 相对路径 | 完整 URL 示例 | 说明 |
|------|----------|---------------|------|
| GET | `""` | `/api/v1/my-words` | 分页列表；query: `status=learning\|mastered`, `page`, `pageSize` |
| POST | `""` | `/api/v1/my-words` | body: `{ "words": ["abandon"] }` — 加入生词本（`is_master=false`） |
| POST | `/master` | `/api/v1/my-words/master` | body: `{ "wordIds": [...] }` 或 `{ "words": [...] }` — 标记掌握 |
| DELETE | `/{wordId}` | `/api/v1/my-words/{wordId}` | 移除复习中词条；`wordId` = **`word_book.id`**（词典单词 ID，非 record id） |

**业务规则**：

- 加入时按 `word_book.word` 查 id；词库无该词 → 400
- 已有 `is_master=true` → 返回提示，不降级
- 已有 `is_master=false` → 幂等成功
- 标记掌握：创建或更新为 `is_master=true`，更新 `user.word_number`（与 `learn.save_word_master` 逻辑统一）
- **生词 → 掌握**：若已有 `is_master=false` 记录，改为 `true` 且 **仅当此前未计掌握数时** 递增 `word_number`（不重复计数）
- **课程学词**：`save_word_master` 重构后仅委托 `mark_mastered`；不涉及 `CourseRecord` 写操作，但须回归验证 `word_number` 与 `/learn/word/master` 行为不变
- 列表返回词条详情（join `WordBook`）：word, phonetic, definition, translation, wordId, isMaster, createdAt

### 3.2 服务层（`server/app/services/my_words.py`）

- `list_my_words(db, user_id, status, page, page_size)`
- `add_words(db, user_id, words: list[str])`
- `mark_mastered(db, user_id, *, word_ids=None, words=None)`
- `remove_word(db, user_id, word_id)`

**重构**：`server/app/services/learn.py` 的 `save_word_master` 改为调用 `mark_mastered`，避免重复。

### 3.3 前端

| 项 | 说明 |
|----|------|
| 路由 | `/my-words` — 「我的生词本」；`meta: { requiresAuth: true }` |
| Tab | 「复习中」/「已掌握」 |
| 词库页 | `WordBook/index.vue` 卡片增加「加入生词本」按钮 |
| API | `apps/web/src/apis/my-words/index.ts` |
| 类型 | `packages/common/word/index.ts` 扩展 `MyWord`, `MyWordList`, `AddWordsDto` |

### 3.4 Agent 工具（可选同步）

`progress_query` / 新 tool `my_words_list` 不在 Phase 0 强制；Phase 3 MCP 优先。

---

## 4. Phase 1 — MCP 基础三 Tool

### 4.1 目录

```
server/english_mcp/          ← 本地包名（禁止用 mcp，见 §2.2）
  __init__.py
  __main__.py                # python -m english_mcp
  server.py                  # FastMCP + lifespan
  config.py                  # MCPSettings
  auth.py                    # resolve_user_id(), rate_limit_key
  db.py                      # init_db / dispose_db
  rate_limit.py              # grammar 15/min
  tools/
    lookup_words.py
    check_grammar.py
    get_progress.py
```

依赖：PyPI **`mcp`**（官方 SDK，`from mcp.server.fastmcp import FastMCP`）。本地包 **`english_mcp`** 与 SDK 包 **`mcp`** 并存，互不覆盖。

### 4.2 Tools

| Tool | 输入 | 输出 | 鉴权 |
|------|------|------|------|
| `lookup_words` | `words`（见下） | JSON 词条数组 | 无 |
| `check_grammar` | `text: str` | 纯文本语法报告 | 无；MCP 层限流 |
| `get_learning_progress` | 无 | JSON 进度 | Key → user_id；无 Key → demo |

**`lookup_words` 输入兼容**（审查修订）：

- Tool schema 仍声明 `words: list[str]`（支持批量）；Claude 通常会按 schema 传 `["abandon"]`，这是**主路径**
- **MCP handler 防御性归一化**（兜底，非主路径）：若偶发传入单个 `str`，自动转为 `["abandon"]` 再调 service；其他 MCP Host 或模型越 schema 时也适用
- `app/services/word_lookup` 层签名保持 `list[str]`；归一化仅在 `english_mcp/tools/lookup_words.py`（及可选 LangChain tool wrapper）完成

`grammar_service.check_grammar(text)` **不含 user_id**；限流在 `english_mcp/tools/grammar.py`。

### 4.3 配置（`server/.env.example` 新增）

```env
ENGLISH_MCP_API_KEY=
ENGLISH_MCP_USER_ID=
ENGLISH_MCP_DEMO_USER_ID=
MCP_DB_POOL_SIZE=5
MCP_DB_MAX_OVERFLOW=10
```

### 4.4 Claude Code CLI 接入

项目根 `.mcp.json` **追加** `english` entry（保留现有 `pencil`）；`server/.env` 由 Python 内 `Path(__file__)` 解析，json 仅：

```json
{
  "english": {
    "type": "stdio",
    "command": "uv",
    "args": ["run", "--directory", "server", "python", "-m", "english_mcp"],
    "env": {
      "ENGLISH_MCP_API_KEY": "${ENGLISH_MCP_API_KEY:-}",
      "ENGLISH_MCP_USER_ID": "${ENGLISH_MCP_USER_ID:-}"
    }
  }
}
```

Windows spawn 失败时 fallback：`cmd /c uv run --directory server python -m english_mcp`。

### 4.5 冒烟脚本

- `server/scripts/smoke_mcp_tools.py` — 不经过 stdio，直接调 services + tool handlers
- 路径说明：`server/scripts/` 为**现有目录**（与 `smoke_chat_agent.py`、`run_agent_eval.py` 等同级），无需新建

---

## 5. Phase 2 — MCP 内容扩展

| Tool | 说明 | 备注 |
|------|------|------|
| `search_knowledge` | 知识库 RAG | 可能冷启动 embedding；脚本测通后再答辩 |
| `list_courses` | 在售课程列表 | 只读 |
| `recommend_courses` | 推荐 1～3 门 | 只读，无购课 |

**MCP Resources（只读）**：

| URI | 内容 |
|-----|------|
| `english://courses/catalog` | 课程 JSON |
| `english://user/progress` | 当前 user 进度 JSON（需 Key） |

---

## 6. Phase 3 — 生词本 MCP + 可选 HTTP

### 6.1 MCP Tools（依赖 Phase 0 `my_words` service）

| Tool | 说明 |
|------|------|
| `list_my_words` | query: `status=learning\|mastered` |
| `add_words_to_review` | 加入生词本 |
| `mark_words_mastered` | 标记掌握 |

均需 MCP 鉴权（Key 或 demo user）。

### 6.2 可选：Streamable HTTP

- `server/english_mcp/http_server.py` — 独立端口如 `3002`
- 答辩不依赖；spec 仅预留

### 6.3 可选：`platform_health` tool

- DB ping、词库 count、DeepSeek 配置是否 present

---

## 7. 不在范围

- 购课 / `web_search` MCP 暴露
- 双向 MCP（平台消费 LangSmith MCP）
- Admin MCP Key 管理 UI
- ClickHouse

---

## 8. 分阶段验收

### Phase 0

1. 登录用户 POST 加入 `abandon` → GET `status=learning` 可见
2. POST master → 出现在「已掌握」，`user.word_number` 增加
3. 词库列表页「加入生词本」可用
4. 课程学词 `save_word_master` 行为不变

### Phase 1

1. `uv run python -m english_mcp` stdio 启动无报错
2. Claude CLI `/mcp` 显示 english connected
3. 三 tool 冒烟脚本通过
4. 答辩 demo：查词 / 语法 / 进度

### Phase 2

1. `search_knowledge` 返回知识库片段
2. `list_courses` / `recommend_courses` 返回合理 JSON
3. Resources 可读

### Phase 3

1. MCP 生词本三 tool 与 Web API 结果一致
2. （可选）HTTP MCP 本地 curl 通

---

## 9. 答辩叙事（30 秒）

> 平台提供 Web 生词本与课程学习闭环；核心能力通过 MCP Server 开放给 Claude Code CLI，查词、语法、进度与知识库、推荐、生词本同步共用业务层；Agent 评测与 LangSmith tracing 保障 AI 质量。

---

## 10. 文档与计划

- 实现计划：`docs/superpowers/plans/2026-06-29-english-mcp-vocabulary.md`
- 依赖顺序：**Phase 0 → 1 → 2 → 3**，每阶段可独立验收

---

## 11. 文档修订记录

| 日期 | 修订 |
|------|------|
| 2026-06-29 | 初稿 |
| 2026-06-29 | 审查修订：`lookup_words` 兼容 str/list；`mark_mastered` 生词→掌握不重复计数；明确 `scripts/` 为现有目录；课程学词重构须回归验证 |
| 2026-06-29 | 澄清：`lookup_words` schema 主路径为 `list[str]`，str 归一化为防御性兜底 |
| 2026-06-29 | 自查修复：包名 `english_mcp`（避免与 PyPI `mcp` 冲突）；API 路径表修正；service 文件名与 plan 对齐；`requiresAuth`；`.mcp.json` 追加而非覆盖 |
| 2026-06-29 | 去重 §3.1 前缀说明；§2.2 补充 hatch packages 含 `english_mcp` |

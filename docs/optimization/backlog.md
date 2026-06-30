# 性能 / 体验 / 功能 backlog

> 记录实测问题与功能缺口，供后续整体优化时排期。未列入当前 sprint。

---

## PERF-001 — Fetch 查询完成后 LLM 回复严重延迟

**状态：** 已记录，待整体优化阶段处理  
**发现日期：** 2026-06-30  
**报告人：** 本地 E2E（维基 Main Page 查词场景）

### 现象

- 用户发送带白名单 URL 的消息（例：`https://en.wikipedia.org/wiki/Main_Page 这个网页有哪些重要单词？`）。
- 前端很快显示工具阶段 **「查询完成」**（`fetch__fetch_url` / 预抓取 SSE 结束）。
- **之后约 2 分钟** 才开始流式输出正文回复；期间界面长时间空白，体验像「卡死」。

### 可能原因（待 profiling 验证）

1. **预抓取 HTML 整页注入 prompt**（`chat.py` preload + `fetch_server` 最多 ~50k 字符），上下文过大，DeepSeek 首 token 慢。
2. **Agent 多轮**：抓取完成后仍可能再调 `word_lookup` 等工具，叠加延迟。
3. **工具完成 → 模型开始生成** 之间无中间态 UI（用户只能看到「查询完成」）。
4. **Windows / 本地 dev** 下 AI 服务、checkpointer、网络叠加（生产环境需复测）。

### 相关代码

| 模块 | 路径 |
|------|------|
| URL 预抓取与 prompt 注入 | `server/ai/services/chat.py` |
| Fetch sidecar 正文长度上限 | `server/external_mcp/fetch_server.py`（`MAX_BODY_CHARS`） |
| SSE 工具 / 聊天事件 | `server/ai/services/sse_adapter.py` |
| 前端工具态展示 | `apps/web/src/views/Chat/` |

### 后续优化方向（备忘）

- [ ] 抓取结果 **HTML → 可读正文/摘要** 再注入，或限制注入长度（如前 8k 字符 + 说明已截断）。
- [ ] 预抓取成功后 **流式提前提示**（「正在分析网页…」），避免 2 分钟空白。
- [ ] 查词场景：**批量 word_lookup** 或限制调用次数，避免 N 次串行工具。
- [ ] 对 `fetch_url_mode` 考虑 **轻量 prompt / 跳过 knowledge_search 以外的多余工具**。
- [ ] 生产与本地分别打点：preload 耗时、checkpointer、LLM TTFT、工具轮次。

### 验收标准（优化后）

- 同类维基首页查词：**「查询完成」→ 首字输出** ≤ 15s（本地 dev，DeepSeek 正常时）。
- 用户感知：工具完成后 **≤3s 内** 有加载态或首段文字，无长时间空白。

---

## FEAT-001 — 聊天内「加入生词本」工具缺失

**状态：** 已记录，待整体优化阶段处理  
**发现日期：** 2026-06-30  
**场景：** Fetch + 维基查词后，用户说「把这些单词都放到生词本中」，AI 回复「没有将单词加入生词本的功能权限」。

### 现象

- 智能助手能 **查词**（`word_lookup`）、**查进度**（`progress_query`），但无法执行 **批量加入生词本**。
- 用户预期：对话里刚列出的单词（如 encyclopedia、feature、article…）一键写入「生词本 → 复习中」。
- 模型只能口头拒绝或误引导为 `progress_query`（该工具仅查询，不能写入）。

### 根因

| 能力 | 状态 |
|------|------|
| 后端 `my_words` API / Service | ✅ 已有（`app/services/my_words.py` → `add_words`） |
| English MCP `add_words_to_review` | ✅ 已有（外部 Claude 等可用） |
| **Web 聊天 Agent 工具** | ❌ **未挂载**（`ai/services/tools/__init__.py` 无对应 tool） |

### 后续实现方向（备忘）

- [ ] 新增 LangChain 工具，如 `add_my_words` / `add_words_to_review`，绑定 `user_id`，调用 `add_words(db, user_id, words)`。
- [ ] 在 `make_tools` 中挂载到 **normal** 角色；prompt 说明：用户说「加入生词本 / 收藏这些词」时调用，单词列表来自上文或参数。
- [ ] 处理 **词库不存在**（`skipped`）与 **已在生词本** 的反馈，工具返回结构化结果供模型转述。
- [ ] 可选：与 Fetch+查词流程联动（「查完词 → 用户确认 → 批量 add」），前端可展示「已加入 N 个词」卡片。
- [ ] 复用 `english_mcp/tools_handlers.run_add_words_to_review` 逻辑，避免双份实现。

### 相关代码

| 模块 | 路径 |
|------|------|
| 生词本业务 | `server/app/services/my_words.py` |
| REST API | `server/app/routers/my_words.py` |
| MCP 已有实现 | `server/english_mcp/tools_handlers.py`（`run_add_words_to_review`） |
| 聊天工具注册 | `server/ai/services/tools/__init__.py` |
| 角色 prompt | `server/ai/services/prompt.py` / LangSmith Hub |

### 验收标准（实现后）

- 用户：「把上面这些词都加入生词本」→ 工具调用成功，生词本「复习中」可见对应词条。
- 词库中不存在的词：明确告知 skipped 原因，不误报成功。
- 与 `word_lookup`、Fetch 查词场景 E2E 通过。

---

## 变更日志

| 日期 | 说明 |
|------|------|
| 2026-06-30 | 创建 backlog；记录 PERF-001（Fetch 完成后 ~2min 才回复） |
| 2026-06-30 | 记录 FEAT-001（聊天内加入生词本工具缺失） |

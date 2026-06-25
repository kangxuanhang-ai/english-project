# 全量上线就绪修复 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按设计文档分 7 阶段关闭审计 P0/P1/P2 项，建立可部署、可 QA 的上线基线。

**Architecture:** 阶段 1→7 顺序执行，每阶段结束跑对应 QA 子集；AI 服务与主 API 可独立部署验证。

**Tech Stack:** Python FastAPI, SQLAlchemy, Alembic, LangGraph, Vue 3, TypeScript, pnpm workspace

**设计文档:** [2026-06-25-launch-readiness-full-fix-design.md](../specs/2026-06-25-launch-readiness-full-fix-design.md)

**前置:** Phase 1 稳定性、五合一功能、Chat 方案 B 推荐卡片已部分落地

---

## 阶段 1 — 环境与数据基线

**验收:** 新 clone → copy `.env.example` → migrate → seed → `pnpm all`

- [x] **Task 1.1:** 修复 Alembic greenfield migration（BE-01）
  - Modify: `server/alembic/versions/` 新增或替换 initial revision
  - Verify: 空 PostgreSQL 上 `uv run alembic upgrade head` 成功

- [x] **Task 1.2:** 词库 seed 路径与 CSV（BE-05, OPS-01）
  - Modify: `server/seed.py`
  - Add: `server/data/ecdict.sample.csv` 或文档说明外部 CSV 路径
  - Verify: CSV 缺失时 exit code 1

- [x] **Task 1.3:** Settings 解耦（BE-06）
  - Modify: `server/app/config.py`
  - Verify: 主 API 在无 DEEPSEEK/BOCHA env 时可启动

- [x] **Task 1.4:** 环境变量示例（BE-07, BE-16, FE-01, FE-02）
  - Add: `server/.env.example`, `apps/web/.env.example`
  - Note: `server/.env.example` 须含 `CORS_ORIGINS` JSON 数组格式示例，如 `["http://localhost:8080"]`

- [x] **Task 1.5:** 部署反代示例（OPS-04）
  - Add: `docs/deploy/nginx.example.conf`（`/api`, `/ai`, `/socket.io`）

- [x] **Task 1.6:** 前端 md5 依赖（FE-04）
  - Modify: `apps/web/package.json`
  - Verify: `pnpm --filter @en/web build`

- [x] **Task 1.7:** seed 价格注释（BE-14）
  - Modify: `server/seed.py` 注释高价课程用途

---

## 阶段 2 — 支付与鉴权

**验收:** QA-05, QA-03, QA-09 子集

- [x] **Task 2.1:** 支付 notify/sync 金额校验（BE-02, BE-03, BE-21）
  - Modify: `server/app/services/pay.py`, `server/app/schemas/pay.py`

- [x] **Task 2.2:** sync 路径 Socket 推送（BE-31）
  - Modify: `server/app/services/pay.py` — `sync_payment_status` 中 `notify_socket=True`

- [x] **Task 2.3:** 防重复 pending 订单（BE-04）
  - Modify: `server/app/services/pay.py`

- [x] **Task 2.4:** Pay.vue 按钮锁定（FE-10）
  - Modify: `apps/web/src/views/Course/components/Pay.vue`

- [x] **Task 2.5:** notify URL 与 POST-only（BE-19, BE-20）
  - Modify: `server/app/routers/pay.py`, 文档

- [x] **Task 2.6:** 路由鉴权 guard（FE-06, FE-07, FE-15）
  - Modify: router, `apps/web/src/apis/auth/index.ts`

- [x] **Task 2.7:** openPay login catch（FE-11）
  - Modify: `apps/web/src/views/Course/index.vue`, `useCourseAction.ts` 等购课入口
  - Verify: 未登录/关弹窗无 unhandled rejection，Pay 不打开

- [x] **Task 2.8:** 登录/注册错误态（FE-09）
  - Modify: `LoginForm.vue`, `RegisterForm.vue`

- [x] **Task 2.9:** Socket token refresh（FE-12）
  - Modify: `useSocket.ts` 或等价 hook

- [ ] **Task 2.10:** Refresh rotation（BE-09，可选本阶段或阶段 5）
  - Modify: `server/app/services/auth.py`

- [x] **Task 2.11:** pay/refresh 限流（BE-22）
  - Modify: routers + rate_limit

---

## 阶段 3 — AI 核心稳定

**验收:** QA-04, QA-06, QA-10

- [x] **Task 3.1:** SSE done/error finally（AI-01, AI-19）
  - Modify: `server/ai/services/chat.py`, `server/ai/routers/chat.py`
  - Modify: `apps/web/src/views/Chat/components/ChatArea.vue`
  - Note: `finally` yield 需 catch `GeneratorExit` / `RuntimeError` / `CancelledError`

- [x] **Task 3.2:** prefer_different fallback（AI-03）
  - Modify: `server/ai/services/recommendation.py`

- [x] **Task 3.3:** parseRecommendBlock 对齐后端（AI-04）
  - Modify: `apps/web/src/views/Chat/parseRecommendBlock.ts`（解析 `__RECOMMEND_JSON__` marker，与 `_extract_recommend_block` 同规则）
  - Related: `ChatArea.vue` 调用方；`ChatRecommendBlock.vue` 仅展示 props，**不需改解析逻辑**
  - Optional: `sanitizeContent.ts` 若 marker  strip 规则需与解析对齐

- [x] **Task 3.4:** 推荐单次 fetch（AI-10）
  - Modify: `server/ai/services/chat.py`, `server/ai/services/tools/recommend.py`

- [x] **Task 3.5:** 历史加载错误态（AI-07, FE-25）
  - Modify: `ChatArea.vue`

- [x] **Task 3.6:** WordBook syncLearningToAi（AI-08）
  - 已在 `Course/Learn/index.vue` 掌握单词后调用；词库页无掌握操作，无需改动

- [x] **Task 3.7:** prompt 与 500 cap 一致（AI-05）
  - Modify: `server/ai/services/prompt.py`, `user_context.py`

- [x] **Task 3.8:** checkpoint 损坏不删 thread（AI-06）
  - Modify: `server/ai/services/chat.py`

- [x] **Task 3.9:** Learn courseId watch（FE-03）
  - Modify: `apps/web/src/views/Course/Learn/index.vue`

- [x] **Task 3.10:** batch-status 失败重试（FE-05）
  - Modify: `CourseRecommendList.vue`, `ChatRecommendBlock.vue`

- [x] **Task 3.11:** Chat ensureValidToken 失败提示（FE-08）
  - Modify: `ChatArea.vue`

---

## 阶段 4 — AI 安全、缓存与限流

**验收:** QA-08

- [x] **Task 4.1:** 推荐缓存 Redis 可选（AI-02）
  - Modify: `server/ai/services/recommendation.py`

- [x] **Task 4.2:** recommend/title/grammar 限流（AI-09, AI-16, AI-17）
  - Modify: `server/ai/routers/`, `rate_limit.py`

- [x] **Task 4.3:** Bocha 结果 sanitize（AI-11）
  - Modify: `server/ai/services/tools/search.py`, `chat.py`

- [x] **Task 4.4:** webSearch 时禁用 web_search tool（AI-12）
  - Modify: `server/ai/services/chat.py`

- [x] **Task 4.5:** JSON 过滤与 prompt 收紧（AI-13, AI-14）
  - Modify: `sanitizeContent.ts`, `prompt.py`

- [x] **Task 4.6:** course_id 规范化（AI-15）
  - Modify: `server/ai/services/recommendation.py`

- [x] **Task 4.7:** SSE 429 提示（AI-18）
  - Modify: `apps/web/src/apis/sse/index.ts`

- [x] **Task 4.8:** learningSync 失败 toast（AI-20）
  - Modify: `apps/web/src/utils/learningSync.ts`

- [x] **Task 4.9:** prompt/list 鉴权（AI-25）
  - Modify: `server/ai/routers/prompt.py`

---

## 阶段 5 — 后端运维与 Tracker

- [x] **Task 5.1:** Tracker 限流与 payload cap（BE-08）
- [x] **Task 5.2:** MinIO init_bucket on startup（BE-11）
- [x] **Task 5.3:** 外部 client lazy init（BE-13）
- [x] **Task 5.4:** 全局 Exception handler（BE-17）
- [x] **Task 5.5:** postgres URL normalize（BE-18）
- [x] **Task 5.6:** ClickHouse config 清理（BE-24）
- [x] **Task 5.7:** GET /health（BE-25）
- [x] **Task 5.8:** logging 结构化（BE-26）
- [x] **Task 5.9:** SECRET_KEY 校验（BE-27）
- [x] **Task 5.10:** seed non-zero exit（BE-15）
- [x] **Task 5.11:** paymentSuccess payload 扩展（BE-30）
  - Modify: `server/app/services/socket.py`, `apps/web/src/views/Course/components/Pay.vue`
  - Payload: `{ userId, courseId, outTradeNo }`

---

## 阶段 6 — 前端体验补齐

- [x] **Task 6.1:** LearningDashboard 错误态（FE-13）
- [x] **Task 6.2:** Course encodeURIComponent（FE-14）— 已实现
- [x] **Task 6.3:** Course/WordBook loading（FE-16）
- [x] **Task 6.4:** 忘记密码 UX（FE-17）— 登录弹窗显示「暂未开放」
- [x] **Task 6.5:** RoleList await setRole（FE-18）
- [x] **Task 6.6:** Setting/Search 错误处理（FE-19～21）
- [x] **Task 6.7:** 历史 50 条提示（AI-21）
- [x] **Task 6.8:** 流式切换对话 abort（AI-23）— 阶段 3 已完成
- [x] **Task 6.9:** 标题生成 fallback（AI-24）
- [x] **Task 6.10:** 口语 pill 文案（AI-27）
- [x] **Task 6.11:** 历史非推荐 tool 还原（AI-22）
- [x] **Task 6.12:** 更新 CLAUDE.md JWT（DOC-01）

---

## 阶段 7 — 全量 QA 与文档

- [x] **Task 7.1:** 执行 QA-01～QA-10 并记录结果 — 见 `docs/qa/2026-06-25-launch-readiness-qa.md`（QA-01/02 自动通过，QA-03～10 待人工）
- [x] **Task 7.2:** 更新 README / AGENTS.md 部署章节（DOC-02, DOC-03）
- [x] **Task 7.3:** `.gitignore` 整理 dist / `.venv`（DOC-04）

---

## 提交建议

每阶段一个 PR，标题格式：

```
fix(launch): phase N — <阶段名>
```

例如：`fix(launch): phase 3 — AI core stability`

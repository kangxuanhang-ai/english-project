# 全量上线就绪修复设计说明书

> 日期：2026-06-25  
> 状态：**待实施**  
> 范围：AI 服务、主后端、前端、部署与工程化 — 审计清单 90+ 项全量修复  
> 目标：答辩与生产部署前，消除已知 P0/P1/P2 问题，建立可验证的上线基线  
> 配套实施计划：`../plans/2026-06-25-launch-readiness-full-fix-plan.md`  
> 前置文档：  
> - [2026-06-23-phase1-stability-fixes-design.md](./2026-06-23-phase1-stability-fixes-design.md)  
> - [2026-06-24-pre-defense-optimization-design.md](./2026-06-24-pre-defense-optimization-design.md)  
> - [2026-06-24-five-features-design.md](./2026-06-24-five-features-design.md)

---

## 1. 背景与动机

### 1.1 现状

项目在答辩前已完成 Phase 1 安全、五合一功能（TTS / 口语 / 看板 / 聊天气泡推荐）、Chat UI 重构等。经 2026-06-25 全栈审计，仍存在约 **90+ 跟踪项**，涵盖：

| 域 | 典型问题 |
|----|----------|
| AI | SSE 生命周期不完整、推荐卡片刷新丢失、限流缺失、prompt 与工具能力不一致 |
| 后端 | Alembic 新库不可用、支付金额未校验、重复下单、Settings 耦合 AI 环境变量 |
| 前端 | 缺 `.env.example`、鉴权边界、静默失败、Learn 页 courseId 不响应 |
| 工程化 | 缺部署反代模板、health check、QA 清单 |

近期 Chat 推荐（方案 B：气泡内 `ChatRecommendBlock`）已落地，但暴露了 **持久化、流式过滤、文案与卡片不一致** 等深层问题。

### 1.2 用户决策

**全量修复后再考虑上线** — 本 spec 为唯一范围权威，覆盖审计 P0/P1/P2（明确 defer 项除外）。

### 1.3 与既有 spec 的关系

| 文档 | 关系 |
|------|------|
| Phase 1 stability | 已完成项作为基线，不重复实现 |
| Pre-defense optimization | 支付幂等、role 校验等已做；本 spec **扩展**金额校验、重复下单等 |
| Five features | 聊天气泡推荐（方案 B）已定；本 spec **完善**持久化、解析、文案一致性 |
| Chat issues fix | 流式 Markdown 等已部分落地；本 spec **收口** SSE done/error |

### 1.4 成功标准（Definition of Done）

1. 新环境：`alembic upgrade head` + `seed.py` 可完成（词库有数据或明确降级策略）
2. `pnpm --filter @en/web build` 通过
3. QA 清单 QA-01～QA-10 全部通过
4. P0 + P1 项 **100% 关闭**；P2 项 **100% 关闭**或文档化接受风险
5. 提供 `server/.env.example`、`apps/web/.env.example`、部署反代示例

---

## 2. 范围边界

### 2.1 改造范围

| 域 | 路径 | 改动类型 |
|----|------|----------|
| AI 聊天 | `server/ai/services/chat.py`, `routers/chat.py` | SSE、历史、过滤、限流 |
| AI 推荐 | `server/ai/services/recommendation.py`, `tools/recommend.py` | 缓存、fallback、单次 fetch |
| AI 工具/上下文 | `server/ai/services/tools/*`, `user_context.py`, `prompt.py` | 限流、prompt 对齐、WordBook sync |
| 主 API 配置 | `server/app/config.py` | Settings 解耦 |
| 支付 | `server/app/services/pay.py`, `routers/pay.py` | 金额校验、防重复单、Decimal |
| 鉴权/用户 | `server/app/services/user.py`, `auth.py`, `routers/user.py` | Refresh 轮换、限流 |
| Tracker | `server/app/routers/tracker.py` | 鉴权或限流 + payload 上限 |
| 数据库 | `server/alembic/versions/` | 新库可用 migration |
| Seed | `server/seed.py` | CSV 路径、价格、失败 exit code |
| 共享/运维 | `server/shared/*`, `server/app/main.py` | MinIO init、health、异常 handler |
| Chat 前端 | `apps/web/src/views/Chat/**` | SSE、历史、推荐卡片、错误态 |
| 业务前端 | `Course/`, `WordBook/`, `Home/`, `Login/`, `apis/` | bug、loading、auth |
| 部署 | `docs/`, `apps/web/vite.config.ts` | env 示例、nginx 示例 |
| 类型 | `packages/common/chat/index.ts` | 历史消息结构 |

### 2.2 明确不在范围（或单独决策）

| 项 | 决策 |
|----|------|
| 欢迎页快捷卡片改版 | 用户暂搁置；不纳入本 spec |
| 密码 MD5 → 明文/Web Crypto 大改 | 保留 MD5+bcrypt，文档标注；全量 HTTPS 下后续迭代 |
| ClickHouse 完整实现 | **移除误导性配置**或 stub 标注「未实现」；不写 analytics 功能 |
| BE-14 seed 部分高价课程 | 产品保留 ¥80000 演示价时，seed 注释 + 答辩脚本 **禁止点击支付** |
| 多 worker 生产拓扑 | 限流/推荐缓存 **可配置 Redis** 或文档限定单 worker |
| NestJS 遗留清理 | 低优先级，不阻塞 |
| AI-26 SSE 推送完整 tool input/output | DevTools 可见性/信息泄露；生产环境可 redact，**答辩后**再细化 |
| BE-32 手写 Alipay 验签 vs 官方 SDK | 沙箱可用；**后续迭代**迁移 SDK，本 spec 仅文档标注 |

### 2.3 禁止修改

- 全局视觉 redesign（角色剧场、口语 Studio 视觉已定）
- 数据库业务表结构大改（除 migration 修复外）
- 更换 LLM 供应商

---

## 3. 架构原则

1. **Fail-safe SSE**：任何 stream 结束路径必须 emit `done` 或 `error`
2. **Single source of truth**：推荐数据 tool 返回与 SSE/history 共用同一 JSON 结构
3. **Silent failure 清零**：用户可见路径必须有 loading / error / retry
4. **Config 分离**：`app/config.py` 与 `ai/config.py` 各取所需，主 API 不依赖 DeepSeek/Bocha
5. **Defense in depth 支付**：签名 + 金额 + 幂等 + 防重复下单
6. **Fail visibly**：静默空态改为 error/retry UI
7. **Prompt 承诺与工具限制一致**：不说「全部单词」若 cap 为 500

---

## 4. 分阶段实施设计

### 阶段 1 — 环境与数据基线（P0）

**目标**：从零可部署、可 seed、可 migrate。

| ID | 设计要点 | 主要改动 |
|----|----------|----------|
| BE-01, OPS-02 | 新增 **greenfield migration** 或重写 initial revision：无 Prisma DROP 依赖 | `alembic/versions/` 新 revision |
| BE-05, OPS-01 | 词库 CSV：仓库内提供 `server/data/ecdict.sample.csv` 或改 seed 读可配置路径；缺失时 **exit 1** | `seed.py`, 文档 |
| BE-07, OPS-03, BE-16 | `server/.env.example` 全量变量 + 注释（含 CORS JSON 数组格式示例） | 新文件 |
| BE-06 | `Settings` 拆为 `AppSettings`；主 API 不 require DEEPSEEK/BOCHA/AI_DATABASE | `app/config.py` |
| FE-01, FE-02, OPS-04 | `apps/web/.env.example`；`docs/deploy/nginx.example.conf` 反代 `/api` `/ai` `/socket.io` | 新文件 |
| FE-04 | `md5` + `@types/md5` 加入 `apps/web/package.json` | package.json |
| BE-14 | seed 异常价格注释化；答辩文档标注 | `seed.py` |

**验收**：新 clone → copy env → migrate → seed → `pnpm all` 可启动。

---

### 阶段 2 — 支付与鉴权（P0 + P1）

| ID | 设计要点 | 主要改动 |
|----|----------|----------|
| BE-02, BE-03 | notify/sync 校验 `total_amount` == `PaymentRecord.amount`（Decimal） | `pay.py` |
| BE-31 | sync 路径 `_fulfill_payment` 改为 `notify_socket=True`（与 notify 一致推送） | `pay.py` |
| BE-04, FE-10 | create_payment 前查 pending 单；Pay.vue 创建订单后 disable 至轮询结束 | `pay.py`, `Pay.vue` |
| BE-21 | 金额全链路 Decimal / Numeric | `schemas/pay.py`, `pay.py` |
| BE-19, BE-20 | notify URL 文档化；notify 仅 POST | `pay.py`, `routers/pay.py` |
| FE-06, FE-07, FE-15 | 路由 guard：无 token 或 refresh 失败 → 弹登录 | `router`, `apis/auth` |
| FE-11 | `openPay` / 购课入口 `login()` catch；未登录不打开 Pay 弹窗 | `Course/index.vue`, `useCourseAction.ts` 等 |
| FE-09 | Login/Register loading + catch + ElMessage | `LoginForm.vue`, `RegisterForm.vue` |
| FE-12 | Socket reconnect 前 `ensureValidToken` | `useSocket.ts`, `App.vue` |
| BE-09 | Refresh token rotation：签发新 refresh 时作废旧 refresh | `auth.py`, `user.py` |
| BE-22 | pay/refresh/tracker 限流 | routers |

**验收**：沙箱支付全流程；sync 轮询路径也能收到 `paymentSuccess`；并发双点支付仅一单；未登录购课无 unhandled rejection；过期 token 正确跳转登录。

---

### 阶段 3 — AI 核心稳定（P0 + P1）

| ID | 设计要点 | 主要改动 |
|----|----------|----------|
| AI-01, AI-19 | `stream_chat` + router：`try/finally` 保证 `done`/`error` | `chat.py`, `routers/chat.py` |
| AI-07, FE-25 | `get_chat_history` 失败 5xx；前端 try/catch + skeleton | `chat.py`, `ChatArea.vue` |
| AI-03 | `prefer_different` 过滤后 courses 为空 → 放宽 exclude 或 fallback | `recommendation.py` |
| AI-04 | `parseRecommendBlock` 与 `_extract_recommend_block` 规则对齐 | `parseRecommendBlock.ts`, `chat.py` |
| AI-10 | tool 内 fetch 一次；SSE enrich **复用 ToolMessage JSON** | `chat.py`, `recommend.py` |
| AI-08 | WordBook 掌握/学习后调用 `syncLearningToAi()` | `WordBook/index.vue` |
| AI-05 | prompt 改为「最多展示 N 个」或提高 cap；二者一致 | `prompt.py`, `user_context.py` |
| AI-06 | checkpoint 损坏：**不 delete thread**；返回 error 提示新建对话 | `chat.py` |
| FE-03 | `watch(() => route.params.courseId)` 重新 `getWordList` | `Learn/index.vue` |
| FE-05 | batch-status 失败：toast + 重试 | `CourseRecommendList.vue`, `ChatRecommendBlock.vue` |
| FE-08 | `ensureValidToken` 失败 ElMessage + 可选 logout | `ChatArea.vue` |

**验收**：推荐 1/3 门、再推荐、刷新、切对话卡片在；SSE 断线不卡死；课程切换词列表更新。

---

### 阶段 4 — AI 安全、缓存与限流（P1）

| ID | 设计要点 | 主要改动 |
|----|----------|----------|
| AI-02 | 推荐缓存：进程内 + **可选 Redis**（env `REDIS_URL`） | `recommendation.py` |
| AI-09 | 限流 `/recommend`, `/conversations/title`, grammar 工具 | routers |
| AI-11 | Bocha 结果 strip HTML/指令；长度截断 | `chat.py`, `llm.py` |
| AI-12 | `webSearch=true` 时 **禁用** agent 的 `web_search` tool | `chat.py` |
| AI-13, AI-14 | 加强 JSON 过滤与 prompt；禁止「没显示出来」类 meta 文案 | `sanitizeContent.ts`, `prompt.py` |
| AI-15 | `_normalize_course_ids` 强制匹配；null id 按 title 补全 | `recommendation.py` |
| AI-16, AI-17 | SlowAPI storage URI 可配置；rate limit key 用 verified userId | `rate_limit.py` |
| AI-18 | SSE 429 → ElMessage「请求过于频繁」 | `sse/index.ts` |
| AI-20 | `learningSync` 失败 toast | `learningSync.ts` |
| AI-25 | `GET /prompt/list` 加 `Depends(get_current_user)` | `routers/prompt.py` |

---

### 阶段 5 — 后端运维与 Tracker（P1 + P2）

| ID | 设计要点 | 主要改动 |
|----|----------|----------|
| BE-08 | Tracker：JWT 可选 + IP 限流 + body size limit | `tracker.py` |
| BE-11 | lifespan 调用 `init_bucket()` | `main.py` |
| BE-13 | lazy init 外部 client | `alipay_client.py`, `minio_client.py` |
| BE-17 | 注册 `@app.exception_handler(Exception)` | `main.py`, `middleware.py` |
| BE-18 | normalize `postgres://` → `postgresql://` | `database.py` |
| BE-24 | ClickHouse：config 改为 Optional；移除空 client 或 README 标注 | `config.py` |
| BE-25 | `GET /health`：DB ping | `main.py` |
| BE-26 | structlog 或 logging config | `main.py` |
| BE-15 | seed 失败 non-zero exit | `seed.py` |
| BE-27 | SECRET_KEY 启动校验（长度/默认值警告） | `config.py` |
| BE-30 | `paymentSuccess` Socket payload 含 `courseId`、`outTradeNo`（不只 userId） | `socket.py`, `Pay.vue` |

---

### 阶段 6 — 前端体验补齐（P2）

| ID | 设计要点 |
|----|----------|
| FE-13 | LearningDashboard error/empty 态 |
| FE-14 | Course index 跳转 `encodeURIComponent(name)` |
| FE-16 | Course/WordBook 绑定 isLoading skeleton |
| FE-17 | 忘记密码：移除链接或「敬请期待」 |
| FE-18 | RoleList await setRole |
| FE-19～FE-21 | Setting/Search loading + 错误处理 |
| FE-22 | Chat 响应式 `@media` 降级（可选） |
| AI-21 | 历史 50 条 UI 提示 |
| AI-22 | 历史还原非推荐类 tool 调用（word_lookup 等气泡内状态/摘要） |
| AI-23 | 流式中切换对话：abort + 提示 |
| AI-24 | 标题生成失败 fallback 截取首条用户消息 |
| AI-27 | 口语 pill 文案与能力对齐 |
| DOC-01 | 更新 CLAUDE.md JWT 说明为 15min |

---

### 阶段 7 — 全量 QA 与文档

执行 **QA-01～QA-10**（见第 6 节），更新 README、AGENTS.md 部署章节，整理 `.gitignore`（dist、`.venv` 等）。

---

## 5. 关键模块设计详述

### 5.1 SSE 生命周期（AI-01）

```
Client POST /chat
  → stream_chat generator
       try:
         async for event in agent.astream_events:
           yield tool/chat/reasoning events
         yield { type: 'done' }
       except OperationalError:
         retry or yield { type: 'error', message }
       except Exception:
         yield { type: 'error', message }
       finally:
         if not emitted_terminal:
           try:
             yield { type: 'error', message: 'stream interrupted' }
           except (GeneratorExit, RuntimeError, asyncio.CancelledError):
             pass  # client disconnected / task cancelled
```

Router 层不得吞掉 terminal event。前端 `onerror` / `done` 必须清除 `isStreaming`、loading 状态。`finally` 中 yield 必须 disconnect-safe，避免客户端断连时 cleanup 再抛错。

### 5.2 推荐数据流（AI-02/04/10）

**目标行为：**

```
User asks → AI intro (content)
         → tool course_recommendation(count, prefer_different)
         → recommendBlock renders in bubble
         → AI summary 2–3 sentences (contentAfter), names match card #1
         → no JSON in text, no "didn't display" meta
```

**数据流：**

```
course_recommendation tool
  → return readable text + __RECOMMEND_JSON__ block
  → ToolMessage 持久化到 checkpointer

SSE on_tool_end
  → parse JSON from tool output（不二次 LLM）

Frontend parseRecommendBlock.ts
  → JSON.parse | extract __RECOMMEND_JSON__ marker（与 Py _extract_recommend_block 同规则）
  → 由 ChatArea.vue 在 SSE on_tool_end 调用；ChatRecommendBlock.vue 仅负责展示 props

get_chat_history
  → fold: intro AIMessage + recommendBlock + contentAfter
```

**History API 消息结构：**

```typescript
{
  role: 'ai',
  type: 'chat',
  content: string,        // intro
  contentAfter?: string,  // summary
  recommendBlock?: {
    courses: CourseRecommendItem[],
    daily_plan?: string,
    summary?: string,
  },
}
```

### 5.3 支付金额校验（BE-02/03）

```python
callback_amount = Decimal(str(params["total_amount"]))
if callback_amount != payment.amount:
    logger.warning("amount mismatch", payment_id=payment.id)
    return "failure"  # 不开课
```

sync 路径同样校验。create 时使用 Decimal，schema 禁止 float 直传。

### 5.4 Settings 解耦（BE-06）

```python
# app/config.py — 仅主 API 所需
class AppSettings(BaseSettings):
    database_url: str
    secret_key: str
    minio_endpoint: str
    # ...
    # 不含: deepseek_*, bocha_*, ai_database_url

# ai/config.py — AI 服务独立，不变
class AISettings(BaseSettings):
    deepseek_api_key: str
    ai_database_url: str
    # ...
```

主 API 启动不应因缺少 `DEEPSEEK_API_KEY` 而失败。

### 5.5 前端鉴权（FE-06/07）

```typescript
router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth) return true
  try {
    await ensureValidToken()
    return true
  } catch {
    showLoginModal()
    return false
  }
})
```

Refresh 失败时清空 token、redirect `/`，与 Axios interceptor 行为一致。

### 5.6 prefer_different fallback（AI-03）

```python
courses = filter_exclude(all_candidates, last_titles)
if not courses and prefer_different:
    courses = all_candidates[:count]  # 放宽 exclude
if not courses:
    courses = fallback_from_db(count)  # 全库 top-N
```

避免「再推荐一门」返回空卡片。

### 5.7 购课登录与 sync 推送（FE-11 / BE-31）

**FE-11：** 未登录用户点击购课时不应产生未处理 Promise rejection。

```typescript
const openPay = async (course: Course) => {
  try {
    await login()
  } catch {
    return // 用户未登录或关闭弹窗，不打开 Pay
  }
  payVisible.value = true
  selectedCourse.value = course
}
```

可选增强：改造 `useLogin().login()` 为「用户登录成功 resolve / 关窗 reject」，而非弹窗一打开即 reject。

**BE-31：** `sync_payment_status` 在 `_fulfill_payment` 成功时应与 notify 路径一致推送 Socket，否则轮询/sync 路径下前端收不到 `paymentSuccess`。

```python
# sync_payment_status — 改为 notify_socket=True
paid = await _fulfill_payment(..., notify_socket=True)
```

### 5.8 支付 Socket payload（BE-30）

现状仅推送 `userId`，多订单并发时前端无法区分。目标 payload：

```typescript
{ userId: string; courseId: string; outTradeNo: string }
```

`Pay.vue` 监听时校验 `outTradeNo` 或 `courseId` 与当前订单一致后再关弹窗。

---

## 6. QA 验收清单

| ID | 场景 | 预期 |
|----|------|------|
| QA-01 | `pnpm --filter @en/web build` | 0 error |
| QA-02 | 新 DB migrate + seed | 成功或有明确失败信息 |
| QA-03 | 注册→登录→refresh→/chat | 正常 |
| QA-04 | 推荐 1/3、再推荐、刷新、切对话 | 卡片+文案一致，无 JSON 泄漏 |
| QA-05 | 支付沙箱全流程 | 金额篡改拒绝；不重复开课；无重复 pending；sync 路径 Socket 正常 |
| QA-06 | 词库学习后推荐变化 | sync 生效 |
| QA-07 | 口语：语音+TTS+grammar | 无 crash |
| QA-08 | 超频 chat/recommend | 429 友好提示 |
| QA-09 | 过期 token / refresh 失败 | logout 或登录弹窗 |
| QA-10 | SSE 模拟服务端异常 | UI 不 stuck，可重发 |

---

## 7. 数据模型 / API 变更

| 区域 | 变更 | 破坏性 |
|------|------|--------|
| History API | AI 消息可选 `recommendBlock`, `contentAfter` | 否（扩展） |
| Recommend tool | 保留 `__RECOMMEND_JSON__` marker | 否 |
| Payment notify | 校验 amount | 否 |
| Payment Socket | `paymentSuccess` 扩展 payload | 否（扩展） |
| Settings | 主 API env 子集 | 否（部署文档更新） |
| Health | 新增 `GET /health` | 否 |

Chat history 不新增 DB 表 — 仍从 LangGraph checkpointer 派生。

---

## 8. 风险与回滚

| 风险 | 缓解 |
|------|------|
| Migration 破坏现有库 | 新 revision 测 greenfield + 现有库双路径 |
| Redis 引入增加复杂度 | 默认内存，生产 env 开启 |
| Refresh rotation 踢掉旧会话 | 前端已处理 401 队列 |
| 全修周期长 | 按阶段 1→7 PR 拆分，每阶段 QA |
| Prompt 改动影响角色性格 | 仅改工具/格式约束段，不动角色人设 |

**回滚**：每阶段独立 branch/PR；AI 与 app 可独立部署。

---

## 9. Issue ID → 阶段跟踪矩阵

| 阶段 | 覆盖 ID |
|------|---------|
| 1 | BE-01,05,06,07,14,16, FE-01,02,04, OPS-01,02,03,04 |
| 2 | BE-02,03,04,09,19,20,21,22,31, FE-06,07,09,10,11,12,14,15 |
| 3 | AI-01,03,04,05,06,07,08,10,19, FE-03,05,08,25 |
| 4 | AI-02,09,11,12,13,14,15,16,17,18,20,25 |
| 5 | BE-08,11,13,15,17,18,24,25,26,27,30 |
| 6 | AI-21,22,23,24,27, FE-13,16,17,18,19,20,21,22,23,24, DOC-01 |
| 7 | QA-01～10, DOC-02,03,04 |
| defer | AI-26, BE-32（见 §2.2） |

审计主 ID 已映射至上表；分组项（如 FE-19～21）见各阶段详表。未列入阶段且不在 defer 表者视为 **Out of scope**（如欢迎页快捷卡片）。

---

## 10. 预估工时

| 阶段 | 人日 |
|------|------|
| 1 环境数据 | 1～2 |
| 2 支付鉴权 | 2～2.5 |
| 3 AI 核心 | 2～3 |
| 4 AI 安全缓存 | 1～2 |
| 5 后端运维 | 1～2 |
| 6 前端体验 | 2 |
| 7 QA 文档 | 1 |
| **合计** | **10～14 人日** |

---

## 11. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-25 | 初稿：全量上线就绪修复范围 |
| v1.1 | 2026-06-25 | 评审补丁：FE-11/BE-31/BE-30/AI-22、SSE disconnect-safe、defer AI-26/BE-32、DoD 对齐 QA-10 |
| v1.2 | 2026-06-25 | BE-16 并入阶段 1；§5.2 澄清 parseRecommendBlock.ts vs ChatRecommendBlock.vue 职责 |

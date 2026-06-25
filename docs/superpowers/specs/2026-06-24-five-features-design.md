# 五合一功能扩展设计（TTS · 口语角色 · 看板 · 推荐跳转 · 聊天购课）

> 状态：**已评审（v2）** — 见文末「已确认决策」与「文档修订记录」。实现计划：`docs/superpowers/plans/2026-06-24-five-features.md`

## 概述

在现有英语学习平台基础上，一次性规划五项关联能力，提升答辩演示完整度与学习闭环：

| # | 功能 | 一句话 |
|---|------|--------|
| F1 | TTS 朗读回复 | AI 消息可朗读；口语考官 / 英语大师角色流式结束后自动朗读 |
| F2 | 口语练习模式 | 新增第 6 聊天角色 `oral`「口语考官」，复用三栏聊天页，默认英文语音输入 + `grammar_check` |
| F3 | 学习数据看板 | **首页内嵌区块**：学习统计 + 埋点活跃 + ECharts + **导出 PNG/PDF** |
| F4 | RecommendCard 直达 | 首页/课程页 AI 推荐卡片 → 已购进学习 / 未购弹支付 |
| F5 | 聊天内推荐购课 | `course_recommendation` 工具返回后渲染课程卡片，复用 `Pay.vue` 支付 |

**已确认的产品决策：**

- 五功能**并行推进**，文档内按依赖分批落地。
- 口语形态：角色代号 **`oral`**，显示名「口语考官」。
- 看板：**完整版**；**嵌入首页**（登录后展示），不设独立 `/dashboard` 路由。
- 看板导出：**需要** PNG + PDF。
- TTS：**手动按钮** + `oral` / `master` **自动朗读**。
- 聊天购课：**仅工具调用**时展示卡片；支付 **复用 Pay.vue**。
- RecommendCard 修复 **纳入本期**，与 F5 **共用组件与购课逻辑**。
- 种子数据托福价格 **保持 ¥80000 不变**。

---

## 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                         apps/web                                 │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│ Chat         │ RecommendCard│ Home         │ hooks               │
│ ChatMessage  │ (F4)         │ LearningDash │ useTTS (F1)         │
│ +CourseRecCard│             │ board (F3)   │ useVoiceToText (F2) │
│ (F5)         │              │              │                     │
│ Pay.vue ─────┴──────────────┴──────────────┘                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
  server/app (3000)      server/ai (3001)      packages/common
  /course/batch-status   role=oral prompt      ChatRoleType +oral
  /user/dashboard        make_tools_by_role    Dashboard types
  /pay/* (已有)          course_recommendation
  /tracker/* (读聚合)
```

**核心复用原则：** F4 与 F5 共用 `CourseRecommendList.vue` + `useCourseAction.ts`，避免两套购买/学习逻辑。

---

## F1 — TTS 朗读回复

### 目标

- 每条 **AI 完成的消息**旁显示 🔊，点击用浏览器朗读正文。
- 角色为 `oral` 或 `master` 时，流式输出 **结束瞬间自动朗读**（可被打断）。
- 不引入付费 TTS 服务；第一版使用 **Web Speech API**（`speechSynthesis`）。

### 前端设计

**新文件：** `apps/web/src/hooks/useTTS.ts`

```ts
interface UseTTSOptions {
  lang?: string       // oral/master 默认 en-US
  rate?: number       // 0.8 ~ 1.0
  autoSpeak?: boolean // 由调用方按角色传入
}
// speak(text), stop(), isSpeaking, supported
```

**改动：** `ChatMessage.vue`

- AI 消息卡片 footer 增加朗读按钮（`item.role === 'ai'` 且 `type === 'chat'` 且有 content）。
- 流式中（`streaming === true`）隐藏自动朗读，仅在 `streaming` 变为 `false` 时触发一次。
- 使用 `watch(() => item.streaming)` + 消息 id 去重，防止重复朗读。
- 新消息开始朗读前调用 `speechSynthesis.cancel()` 打断上一条。

**自动朗读范围：** 仅当 `activeRole ∈ { oral, master }`（由 `ChatArea` 传入 prop `autoTts`）。

### 限制（文档 & 答辩说明）

| 限制 | 说明 |
|------|------|
| 浏览器差异 | Chrome/Edge 体验较好；需用户曾有过页面交互 |
| 中文/英文 | `oral`/`master` 用 `en-US`；其他角色手动点读时用 `zh-CN` 或按内容检测（第一版固定 zh-CN） |
| Markdown | 朗读前 `stripMarkdown(content)` 去 HTML/符号 |

### 不涉及后端改动。

---

## F2 — 口语练习模式（角色 `oral`）

### 目标

新增第 6 个聊天角色「口语考官」：英文提问、纠错、场景化陪练；界面与现有聊天一致。

### 角色定义

| 字段 | 值 |
|------|-----|
| `role` | `oral` |
| 显示名 | 🎙️ 口语考官 |
| 语言 | 英文为主，纠错说明可中英对照 |
| 工具 | **仅** `grammar_check`（无查词/搜索/推荐/进度） |
| 语音输入 | `ChatInputDock` 在 `oral` 下默认 `lang: 'en-US'` |
| TTS | 开启自动朗读（F1） |

### System Prompt（草案）

```
你是一位耐心的英语口语考官（IELTS/日常口语）。
规则：
1. 用英语与用户对话，每次只问一个问题或给一个简短任务。
2. 用户回答后：先简短鼓励，再指出语法/用词问题（可用 grammar_check），给出更自然的说法。
3. 主动引导场景：自我介绍、旅行、面试、看图说话等。
4. 不要输出 JSON；不要提及工具名称。
5. 回复控制在 150 词以内，适合朗读。
```

### 需同步修改的文件（角色贯通清单）

| 层 | 文件 |
|----|------|
| 类型 | `packages/common/chat/index.ts` — `ChatRoleType` 加 `oral` |
| 前端 UI | `roleConfig.ts` — theme/cards/greeting |
| 前端路由 | `router/chat/index.ts`（若有 role 枚举校验） |
| AI Schema | `ai/schemas/chat.py`, `ai/schemas/conversation.py` |
| AI Prompt | `ai/services/prompt.py` — `CHAT_MODES` 新增一项 |
| AI Chat | `ai/services/chat.py` — `make_tools_by_role(user_id, role)` |
| AI Tools | `ai/services/tools/__init__.py` — 导出 `make_tools_by_role` |
| 工具脚本 | `clear_chat_history.py` — roles 列表加 `oral` |
| Agent 缓存 | `grammar_check` 为全局工具、**无 user_id 闭包**，与 `master` 相同 → **`oral` 允许 agent 缓存**，cache key `(oral, deep_think)`；仅 `normal`（per-user tools）与 `web_search` 不缓存 |

### `make_tools_by_role` 设计

```python
def make_tools_by_role(user_id: str, role: str) -> list:
    if role == "normal":
        return make_tools(user_id)  # 现有 5 工具
    if role == "oral":
        return [grammar_check]
    return []
```

---

## F3 — 学习数据看板（首页内嵌）

### 目标

用户**登录后**在首页查看学习成果与活跃情况；支持**导出 PNG / PDF** 用于答辩截图或存档。

### 首页布局位置

```
┌─ Hero（打卡 + 全息图）────────────────────────┐
├─ AI 推荐卡片 RecommendCard（已有，compact）────┤
├─ 📊 我的学习数据 LearningDashboard（新增）─────┤  ← F3 放这里
├─ 为什么选择我们 / 营销统计区（已有）───────────┤
└─ 核心优势 …                                  ┘
```

- **仅登录用户展示**（`v-if="userStore.getUser"`），与 RecommendCard 同级。
- 不设独立路由；顶栏「首页」滚动即可到达（可选：Hero 区加「查看学习数据」锚点 `#learning-dashboard` 平滑滚动）。
- 与下方营销用的静态 `stats` 数组**区分开**：营销区继续写「100万学员」类文案；看板区展示**用户真实数据**。

### 页面结构

```
┌─ 标题行：我的学习数据          [导出 PNG] [导出 PDF] ─┐
├─ 概览卡片 ───────────────────────────────────────────┤
│ 连续打卡 │ 掌握单词 │ 已购课程 │ 本周学习词数            │
├─ 学习趋势 ───────────────────────────────────────────┤
│ 折线图：近 7 天每日新掌握词数                          │
├─ 课程进度 ───────────────────────────────────────────┤
│ 每门已购课程：进度条（已掌握/该课程词库总量）            │
├─ 活跃分析（Tracker）─────────────────────────────────┤
│ 近 7 天 PV 折线图 │ 访问最多页面 Top5                  │
└──────────────────────────────────────────────────────┘
```

### 导出 PNG / PDF

**依赖：** `html2canvas`（截图 DOM）+ `jspdf`（PDF 多页，图表过高时自动分页）。

**新 hook：** `apps/web/src/hooks/useDashboardExport.ts`

```ts
// exportPng(element: HTMLElement, filename)
// exportPdf(element: HTMLElement, filename)
```

- 对看板根节点 `#learning-dashboard` 截图；导出前临时隐藏「导出」按钮（`data-export-hide`）。
- PNG：单张 `learning-report-{date}.png`。
- PDF：标题「英语学习数据报告」+ 用户名 + 生成日期页眉。
- 导出中显示 loading，失败 `ElMessage.error`。

**验收：** Chrome 下 PNG 清晰可读；PDF 包含概览卡片与至少一张图表。

### 后端 API

**新路由：** `GET /api/v1/user/dashboard`（需 JWT）

**响应结构（`DashboardStats`）：**

```json
{
  "overview": {
    "checkInDays": 7,
    "masteredWords": 328,
    "purchasedCourses": 3,
    "wordsThisWeek": 45
  },
  "wordTrend": [
    { "date": "2026-06-17", "count": 12 }
  ],
  "courseProgress": [
    {
      "courseId": "xxx",
      "name": "托福词汇",
      "mastered": 120,
      "total": 3500,
      "percent": 3.4
    }
  ],
  "activity": {
    "pvTrend": [{ "date": "2026-06-17", "count": 8 }],
    "topPaths": [{ "path": "/courses/index", "count": 15 }],
    "totalPv": 120
  }
}
```

**数据来源：**

| 指标 | SQL 思路 |
|------|----------|
| 掌握词数 | `WordBookRecord` where `is_master` |
| 本周新掌握 | `WordBookRecord.created_at` 近 7 天 |
| 打卡天数 | `User.day_number` |
| 课程进度 | 复用 `recommendation._query_user_data` 中按 `Course.value` 统计逻辑 |
| PV 趋势 | 见下方「Tracker 用户关联」 |
| Top 路径 | 同上，按 `path` GROUP BY |

### Tracker 用户关联（PV / 事件）

`page_view` 表**没有** `user_id`，必须通过访客关联：

```text
page_view.visitor_id  →  visitor.id  →  visitor.user_id
```

**聚合 SQL 模式：**

```sql
SELECT date_trunc('day', pv.created_at) AS day, COUNT(*) AS count
FROM page_view pv
JOIN visitor v ON pv.visitor_id = v.id
WHERE v.user_id = :current_user_id
  AND pv.created_at >= :since
GROUP BY day
ORDER BY day;
```

`track_event` 统计（Top 事件）同样 `JOIN visitor`，过滤 `v.user_id = :current_user_id`。

**边界说明（答辩可解释）：**

| 情况 | 行为 |
|------|------|
| 未登录浏览 | PV 挂在匿名 `visitor`，**不计入**个人看板 |
| 登录后 | `Tracker.setUserId()` 更新 `visitor.user_id`，之后 PV 计入 |
| 换设备 / 清缓存 | 新 `anonymous_id` → 新 visitor，历史 PV 不合并 |
| 数据偏少 | 冷启动显示「暂无活跃数据」，Phase 2 补自定义事件埋点 |

**新文件：**

- `server/app/services/dashboard.py`
- `server/app/routers/dashboard.py` 或挂在 `user.py`
- `packages/common/user/index.ts` — `DashboardStats` 类型
- `apps/web/src/views/Home/components/LearningDashboard.vue` — 看板组件
- `apps/web/src/views/Home/index.vue` — 在 RecommendCard 下方引入
- `apps/web/src/hooks/useDashboardExport.ts` — PNG/PDF 导出

### 前端图表

- 引入 **ECharts**（`echarts`；看板组件内动态 `import`）。
- `LearningDashboard.vue` 内 `onMounted` 拉取 `/user/dashboard` 并渲染图表。

### Tracker 补充（可选，建议做）

在关键行为上报自定义事件，便于看板有内容：

| 事件名 | 触发点 |
|--------|--------|
| `course_learn_start` | 进入学习页 |
| `pay_success` | Pay.vue 支付成功 |
| `check_in` | 打卡成功 |

使用现有 `Tracker.reportEvent()`，**不阻塞主流程**。

---

## F4 — RecommendCard 直达课程 / 支付

### 目标

点击 AI 推荐卡片上的行动按钮时：

- **已购买** → `/courses/learn/:courseId/:title`
- **未购买** → 打开 `Pay.vue` 并传入该课程对象

### 实现

1. 抽取 **`CourseRecommendList.vue`**
   - Props: `courses: CourseRecommendation[]`
   - 内部调用 `GET /api/v1/course/batch-status?ids=a,b,c` 获取 `purchased` + `price` + `name` + `teacher` + `url`
   - 每行：`title`、`reason`、`match_score`、按钮「立即购买 ¥xx」/「立即学习」

2. **`useCourseAction.ts`**
   - `openPay(course)` → 设置 `selectedCourse` + `payVisible`
   - `goLearn(course)` → router.push learn 路由

3. **改动 `RecommendCard.vue`**
   - 用 `CourseRecommendList` 替换现有静态列表
   - `handleStartLearn` 删除写死的 `/courses/index`

4. **改动 `Course/index.vue`**
   - 已有 `Pay.vue`；处理 RecommendCard / 课程列表的 `@buy`

### Pay.vue 所有权（三页各一实例）

**不做**全局单例或 provide/inject；每个路由页面**各自挂载一个** `Pay.vue`（Teleport 到 body，互不干扰）。用户同时只在一个路由，不会并行弹出多个 Pay。

| 页面 | Pay.vue 挂载位置 | 谁触发 `@buy` / 打开支付 |
|------|------------------|---------------------------|
| `Home/index.vue` | Home 模板内 | `RecommendCard` → `CourseRecommendList` emit `buy` |
| `Course/index.vue` | Course 模板内（已有） | 课程卡片「购买课程」+ RecommendCard（若展示） |
| `Chat/index.vue` | Chat 模板内 | 聊天内 `course_recommendation` 工具卡片 emit `buy` |

**统一模式：**

```text
CourseRecommendList @buy → 父页 selectedCourse + payVisible=true → Pay.vue
CourseRecommendList @learn → useCourseAction.goLearn() → /courses/learn/...
```

`useCourseAction.ts` 只负责 `goLearn` 路由跳转；**Pay 状态（selectedCourse、payVisible）留在各页面父组件**，避免跨路由共享 ref。

---

## F5 — 聊天内推荐课程 + 快捷购买/学习

### 目标

用户在 **normal 角色** 聊天中触发 `course_recommendation` 工具后，在工具区域展示与 F4 相同的课程卡片，而非纯 JSON 文本。

### 触发条件（已确认）

**仅**当 SSE 收到 `type: 'tool_result'` 且 `tool === 'course_recommendation'` 时渲染卡片。

### 数据流

```
用户: "推荐一门课程"
  → Agent 调用 course_recommendation
  → tool_result 携带 JSON output
  → ChatArea 解析 JSON，挂载 CourseRecommendList
  → batch-status 查购买状态
  → 未购: emit buy → Chat/index.vue 打开 Pay.vue
  → 已购: goLearn
```

### 前端改动

| 文件 | 改动 |
|------|------|
| `ChatMessage.vue` | `tool` 类型且 `toolName === 'course_recommendation'` 且有 `toolOutput` 时，解析 JSON 渲染 `CourseRecommendList` |
| `Chat/index.vue` | 引入 `Pay.vue`，处理 `@buy` |
| `packages/common/chat` | 可选：`toolDisplay: 'course_recommendation'` 标记 |

### 后端改动（增强稳定性）

1. **`recommendation.py`**：后处理校验 `course_id` 必须存在于 DB，否则尝试按 `title` 模糊匹配；仍失败则该条 `course_id=null` 不显示购买按钮，仅展示文案。

2. **新 API `GET /api/v1/course/batch-status`**
   - Query: `ids` 逗号分隔
   - 返回每课：`id, name, price, teacher, url, purchased: boolean`
   - 需登录

### 与 F4 共用

- `CourseRecommendList.vue`
- `useCourseAction.ts`
- `Pay.vue`（倒计时 + sync 轮询逻辑不变）

---

## 共享 API：课程批量状态

```
GET /api/v1/course/batch-status?ids=id1,id2,id_not_exist
Authorization: Bearer <token>

Response.data: [
  {
    "id": "xxx",
    "name": "托福词汇",
    "price": "80000.00",
    "teacher": "枫竹",
    "url": "/course/toefl.png",
    "purchased": false
  }
]
```

**无效 / 不存在 `course_id` 的行为：**

- **不返回 404**；整请求仍 200。
- 仅返回 DB 中**存在**的课程条目。
- 请求里无效 id **静默忽略**（可选在响应加 `missingIds: string[]` 便于调试，前端可不消费）。
- 前端：`CourseRecommendList` 若某条 `course_id` 不在响应中 → 只展示 title/reason，**不显示**购买/学习按钮。

**实现：** `server/app/services/course.py` + `routers/course.py`

---

## 实现分期（并行但分依赖）

### Phase 0 — 基础（阻塞其他项，约 0.5 天）

- [ ] `ChatRoleType` + 后端 Literal 扩展 `oral`（可先合入，UI 后补）
- [ ] `GET /course/batch-status`
- [ ] `CourseRecommendList.vue` + `useCourseAction.ts`
- [ ] `packages/common` 类型更新

### Phase 1 — 可并行（约 2–3 天）

| 轨道 | 任务 |
|------|------|
| A | F4 RecommendCard + Course 页 Pay 联动 |
| B | F5 ChatMessage 工具卡片 + Chat Pay |
| C | F1 useTTS + ChatMessage 朗读按钮/自动朗读 |
| D | F2 oral 角色 prompt + tools + roleConfig + 英文语音 |
| E | F3 dashboard API + `LearningDashboard` 首页嵌入 + ECharts + 导出 |

### Phase 2 — 联调与打磨（约 1 天）

- [ ] 看板 Tracker 事件埋点
- [ ] PNG / PDF 导出联调
- [ ] 口语角色 + TTS 联调（先听后说）
- [ ] 推荐 `course_id` 为 null 的降级 UI
- [ ] 全流程冒烟：聊天推荐 → 购买 → 看板数据更新

---

## 风险与对策

| 风险 | 对策 |
|------|------|
| 推荐 JSON 中 `course_id` 为空 | 后端校验 + 前端隐藏购买钮，仅显示 title/reason |
| Web Speech 浏览器不支持 | 朗读按钮 disabled + tooltip |
| 看板 Tracker 数据少 | Phase 2 补埋点；冷启动显示「暂无活跃数据」 |
| 新增角色遗漏 Literal | 使用清单统一改；`vue-tsc` 会报错 |
| Pay 弹窗多处实例 | 三页各持一个 Pay（Home/Course/Chat），同页仅一个；子组件 emit `buy` 上浮，不用全局单例 |
| 看板 PV 偏少 | 仅统计 `visitor.user_id` 已绑定的 PV；见 F3 Tracker 关联说明 |
| 并行开发冲突 | Phase 0 先合并；F4/F5 共用组件后分叉 |

---

## 不在本期范围

- 付费 TTS（Azure/阿里云）
- 口语发音打分（需第三方 SDK）
- ClickHouse 迁移（看板仍查 Postgres）
- 管理后台
- 课程详情独立页 `/courses/:id`

---

## 验收标准

### F1 TTS
- [ ] AI 消息有朗读按钮，点击可朗读
- [ ] `oral`/`master` 流式结束后自动朗读一次
- [ ] 连续消息不叠读（新消息打断旧朗读）

### F2 口语角色
- [ ] 角色列表出现「口语考官」
- [ ] 可创建会话、流式对话
- [ ] 仅 `grammar_check` 可被调用
- [ ] 语音输入默认英文

### F3 看板
- [ ] 登录后首页 RecommendCard 下方展示看板
- [ ] 展示概览 + 至少 2 张图表
- [ ] 数据与 DB 一致（掌握词数、打卡）
- [ ] Tracker PV 趋势有数据（埋点补完后）
- [ ] 可导出 PNG 与 PDF

### F4 RecommendCard
- [ ] 点推荐课程：已购进学习页，未购弹 Pay
- [ ] 不再跳转到空课程列表

### F5 聊天购课
- [ ] 聊天问「推荐课程」出现卡片
- [ ] 立即购买走 Pay.vue + 支付宝沙箱
- [ ] 已购显示立即学习并跳转

---

## 已确认决策（评审通过）

| 项 | 决策 |
|----|------|
| 看板位置 | **首页内嵌**，放在 AI 推荐卡片下方；登录后可见 |
| 口语角色代号 | `oral`，显示「口语考官」 |
| 托福种子价格 | **不改**，保持 ¥80000（答辩时可说明为沙箱演示价） |
| 看板导出 | **需要** PNG + PDF（html2canvas + jspdf） |

---

## 文档修订记录

| 版本 | 修订内容 |
|------|----------|
| v2 | ① `oral` agent **允许缓存**（grammar_check 无 user 闭包）② F3 补充 PV 经 `visitor.user_id` 关联及边界 ③ Pay.vue 三页所有权表 ④ batch-status 无效 id 静默忽略 ⑤ 托福价保留并加答辩说明 |

---

**下一步：** 按 `docs/superpowers/plans/2026-06-24-five-features.md` 分 Phase 实施。

# 五合一功能扩展 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 F1 TTS、F2 口语角色 `oral`、F3 首页学习看板（ECharts + PNG/PDF 导出）、F4 RecommendCard 直达购课/学习、F5 聊天内推荐购课。

**Architecture:** Phase 0 建立共用类型与 API、推荐组件、Pay 所有权约定 → Phase 1 五轨道并行 → Phase 2 埋点/导出/全流程冒烟。F4/F5 共用 `CourseRecommendList`；三页各持一个 `Pay.vue`；看板嵌入 `Home/index.vue` RecommendCard 下方。

**Tech Stack:** Vue 3, TypeScript, FastAPI, SQLAlchemy, ECharts, html2canvas, jspdf, Web Speech API

**设计文档:** [2026-06-24-five-features-design.md](../specs/2026-06-24-five-features-design.md)（v2 已评审）

**Plan 修订:** v2 — 明确 `CourseRecommendation` 类型来源；`useVoiceToText` 采用方案 A（`setLang` + 重建实例）

**前置:** 支付 sync 轮询、支付幂等、Chat role 校验已完成；无需新数据库 migration。

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `packages/common/chat/index.ts` | Modify | `ChatRoleType` + `'oral'` |
| `packages/common/course/index.ts` | Modify | `CourseBatchStatus`, `BatchStatusResponse` |
| `packages/common/user/index.ts` | Modify | `DashboardStats` 等类型 |
| `server/app/services/course.py` | Modify | `get_courses_batch_status` |
| `server/app/routers/course.py` | Modify | `GET /batch-status` |
| `server/app/services/dashboard.py` | Create | 看板聚合（含 PV JOIN visitor） |
| `server/app/routers/user.py` | Modify | `GET /dashboard` |
| `server/ai/schemas/chat.py` | Modify | Literal + `oral` |
| `server/ai/schemas/conversation.py` | Modify | Literal + `oral` |
| `server/ai/services/prompt.py` | Modify | oral system prompt |
| `server/ai/services/tools/__init__.py` | Modify | `make_tools_by_role` |
| `server/ai/services/chat.py` | Modify | 按 role 选 tools；oral 可缓存 agent |
| `server/ai/services/recommendation.py` | Modify | `_normalize_course_ids` |
| `apps/web/src/components/CourseRecommendList.vue` | Create | 推荐列表 + 购课/学习按钮 |
| `apps/web/src/hooks/useCourseAction.ts` | Create | `goLearn`, `toCourse` 类型转换 |
| `apps/web/src/hooks/useTTS.ts` | Create | Web Speech 朗读 |
| `apps/web/src/hooks/useDashboardExport.ts` | Create | PNG/PDF 导出 |
| `apps/web/src/views/Home/components/LearningDashboard.vue` | Create | 首页看板区块 |
| `apps/web/src/views/Home/index.vue` | Modify | 看板 + Pay + RecommendCard |
| `apps/web/src/components/RecommendCard.vue` | Modify | 接入 CourseRecommendList |
| `apps/web/src/views/Course/index.vue` | Modify | RecommendCard emit（若有） |
| `apps/web/src/views/Chat/index.vue` | Modify | VALID_ROLES + Pay.vue |
| `apps/web/src/views/Chat/roleConfig.ts` | Modify | oral 主题 |
| `apps/web/src/views/Chat/components/ChatMessage.vue` | Modify | TTS + 推荐工具卡片 |
| `apps/web/src/views/Chat/components/ChatArea.vue` | Modify | autoTts + oral 语音 lang |
| `apps/web/src/apis/course/index.ts` | Modify | `getCourseBatchStatus` |
| `apps/web/src/apis/recommend/index.ts` | 已有 | 导出 `CourseRecommendation`（Task 0.3 Step 0） |
| `apps/web/src/apis/user/index.ts` | Modify | `getDashboard` |
| `apps/tracker/index.ts` | Modify | 公开 `trackEvent()` 方法（Phase 2） |
| `apps/web/src/hooks/useVoiceToText.ts` | Modify | 方案 A：`setLang()` 重建 SpeechRecognition |
| `clear_chat_history.py` | Modify | roles + `oral` |
| `apps/web/package.json` | Modify | echarts, html2canvas, jspdf |

---

## Phase 0 — 共用基础（必须先完成）

> **完成标准:** `GET /course/batch-status` 可调用；`CourseRecommendList` 可独立渲染；`oral` 类型后端已通过 Literal 校验。

---

### Task 0.1: oral 类型贯通

**Files:**
- Modify: `packages/common/chat/index.ts`
- Modify: `server/ai/schemas/chat.py`
- Modify: `server/ai/schemas/conversation.py`
- Modify: `clear_chat_history.py`

- [ ] **Step 1:** `ChatRoleType` 改为：

```ts
export type ChatRoleType = 'normal' | 'master' | 'business' | 'qilinge' | 'xiaoman' | 'oral';
```

- [ ] **Step 2:** 两处 Python Literal 均加 `'oral'`：

```python
role: Literal['normal', 'master', 'business', 'qilinge', 'xiaoman', 'oral']
```

- [ ] **Step 3:** `clear_chat_history.py` roles 列表追加 `"oral"`

- [ ] **Step 4:** 验证

```bash
cd server && uv run python -c "from ai.schemas.chat import ChatRequest; print('ok')"
cd apps/web && pnpm type-check
```

预期：`roleConfig.ts`、`Chat/index.vue` VALID_ROLES 等报 TS 错误（Phase 1 轨道 D 修复），后端无报错。

---

### Task 0.2: 课程批量状态 API

**Files:**
- Modify: `server/app/services/course.py`
- Modify: `server/app/routers/course.py`
- Modify: `packages/common/course/index.ts`
- Modify: `apps/web/src/apis/course/index.ts`

- [ ] **Step 1:** 在 `course.py` 末尾添加：

```python
async def get_courses_batch_status(
    db: AsyncSession, user_id: str, course_ids: list[str]
) -> dict:
    if not course_ids:
        return {"items": [], "missingIds": []}

    result = await db.execute(select(Course).where(Course.id.in_(course_ids)))
    courses = {c.id: c for c in result.scalars().all()}
    found_ids = set(courses.keys())
    missing_ids = [cid for cid in course_ids if cid not in found_ids]

    purchased_result = await db.execute(
        select(CourseRecord.course_id).where(
            CourseRecord.user_id == user_id,
            CourseRecord.is_purchased.is_(True),
            CourseRecord.course_id.in_(found_ids),
        )
    )
    purchased_ids = {row[0] for row in purchased_result.all()}

    items = [
        {
            "id": c.id,
            "name": c.name,
            "value": c.value,
            "description": c.description,
            "teacher": c.teacher,
            "url": c.url,
            "price": f"{c.price:.2f}",
            "purchased": c.id in purchased_ids,
        }
        for c in courses.values()
    ]
    return {"items": items, "missingIds": missing_ids}
```

- [ ] **Step 2:** 在 `routers/course.py` 添加（需登录）：

```python
from app.dependencies import get_current_user

@router.get("/batch-status")
async def batch_status(
    ids: str = Query(..., description="逗号分隔课程 ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course_ids = [i.strip() for i in ids.split(",") if i.strip()]
    data = await get_courses_batch_status(db, user["userId"], course_ids)
    return {"data": data, "code": 200, "message": "查询成功"}
```

- [ ] **Step 3:** `packages/common/course/index.ts` 添加：

```ts
export interface CourseBatchStatus extends Course {
    purchased: boolean;
}
export interface BatchStatusResponse {
    items: CourseBatchStatus[];
    missingIds: string[];
}
```

- [ ] **Step 4:** API 封装：

```ts
export const getCourseBatchStatus = (ids: string[]) =>
    serverApi.get('/course/batch-status', {
        params: { ids: ids.join(',') },
    }) as Promise<Response<BatchStatusResponse>>;
```

- [ ] **Step 5:** 验证（需登录 token）

```bash
# 启动 pnpm server 后
curl -H "Authorization: Bearer <token>" \
  "http://localhost:3000/api/v1/course/batch-status?ids=有效id,无效id"
```

预期：200；`items` 仅含有效课程；`missingIds` 含无效 id。

---

### Task 0.3: CourseRecommendList 共用组件

**Files:**
- Create: `apps/web/src/components/CourseRecommendList.vue`
- Create: `apps/web/src/hooks/useCourseAction.ts`
- 已有: `apps/web/src/apis/recommend/index.ts`（无需新建类型文件）

- [ ] **Step 0: 确认 `CourseRecommendation` 类型来源**

类型**已定义**于 `apps/web/src/apis/recommend/index.ts`：

```ts
export interface CourseRecommendation {
    course_id: string | null;
    title: string;
    reason: string;
    match_score: number;
}
```

`CourseRecommendList.vue` / `useCourseAction.ts` / `RecommendCard.vue` 统一：

```ts
import type { CourseRecommendation } from '@/apis/recommend';
```

**本期不迁移**到 `packages/common`（避免 scope 扩大；后端 recommend JSON 结构已对齐）。

- [ ] **Step 1:** `useCourseAction.ts`

```ts
import { useRouter } from 'vue-router';
import type { Course } from '@en/common/course';
import type { CourseBatchStatus } from '@en/common/course';
import type { CourseRecommendation } from '@/apis/recommend';

export function useCourseAction() {
    const router = useRouter();

    const toCourse = (item: CourseBatchStatus): Course => ({
        id: item.id,
        name: item.name,
        value: item.value,
        description: item.description,
        teacher: item.teacher,
        url: item.url,
        price: item.price,
    });

    const goLearn = (course: Course | CourseBatchStatus) => {
        const c = 'purchased' in course ? toCourse(course) : course;
        router.push(`/courses/learn/${c.id}/${encodeURIComponent(c.name)}`);
    };

    return { goLearn, toCourse };
}
```

- [ ] **Step 2:** `CourseRecommendList.vue` 核心逻辑

Props:
```ts
courses: CourseRecommendation[]  // from recommend API / tool output
```

行为:
1. `onMounted`：收集非 null 的 `course_id`，调 `getCourseBatchStatus`
2. 构建 `Map<id, CourseBatchStatus>` 便于查找
3. 每条推荐渲染：
   - `course_id == null` 或 id 不在 map → 只显示 title/reason，无按钮
   - `purchased === true` → 按钮「立即学习」→ `emit('learn', course)`
   - 否则 → 按钮「立即购买 ¥{price}」→ `emit('buy', course)`

Emits: `(e: 'buy' | 'learn', course: CourseBatchStatus)`

UI：与 RecommendCard 风格一致（白底圆角卡片、indigo 按钮）。

- [ ] **Step 3:** 临时在 `Course/index.vue` 底部挂载测试（可选，Phase 1 正式接入）

- [ ] **Step 4:** 验证：传入一条已购 + 一条未购 course_id，按钮文案正确。

---

### Task 0.4: Pay.vue 三页所有权约定（文档级 + 骨架）

**Files:**
- Modify: `apps/web/src/views/Home/index.vue`（Phase 1 轨道 A 实现）
- Modify: `apps/web/src/views/Chat/index.vue`（Phase 1 轨道 B 实现）

- [ ] **Step 1:** 确认 `Course/index.vue` 已有模式：

```vue
const payVisible = ref(false)
const selectedCourse = ref<Course | null>(null)
<CoursePay v-model="payVisible" :course="selectedCourse" @success="onPaySuccess" />
```

- [ ] **Step 2:** Home / Chat 复制相同三行 state + Pay 组件（Phase 1 实现，此处仅标记 checklist）

- [ ] **Step 3:** **禁止** provide/inject 跨页共享 Pay 状态

**Phase 0 门禁:** Task 0.1–0.3、**0.5** 全部勾选后方可进入 Phase 1。

---

### Task 0.5: useVoiceToText 支持 setLang（方案 A，oral 前置）

**Files:**
- Modify: `apps/web/src/hooks/useVoiceToText.ts`

**问题:** 模块级单例 `getInstance()` 仅在首次创建时读取 `lang`，之后切到 `oral` 仍用 `zh-CN` 识别。

**选定方案 A:** 暴露 `setLang()`，语言变化时 **stop → 销毁旧实例 → 新建 SpeechRecognition**。

- [ ] **Step 1:** 重构实例管理

```ts
let instance: SpeechRecognition | null = null
let storedOptions: Options = {}

function createRecognition(options: Options): SpeechRecognition {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SR) throw new Error('SpeechRecognition is not supported in this browser')
  const {
    lang = 'zh-CN',
    continuous = false,
    interimResults = false,
    maxAlternatives = 1,
  } = options
  const rec = new SR()
  rec.lang = lang
  rec.continuous = continuous
  rec.interimResults = interimResults
  rec.maxAlternatives = maxAlternatives
  return rec
}

function rebuildInstance(options: Options): SpeechRecognition {
  try { instance?.stop() } catch { /* 可能未在录音 */ }
  instance = createRecognition(options)
  storedOptions = { ...options }
  return instance
}
```

- [ ] **Step 2:** `useVoiceToText` 返回 `setLang`

```ts
export const useVoiceToText = (options: Options) => {
  let recognition = instance ?? rebuildInstance(options)
  // 若首次 options.lang 与 stored 不同，也 rebuild
  if (options.lang && options.lang !== storedOptions.lang) {
    recognition = rebuildInstance({ ...storedOptions, ...options })
  }

  const isRecording = ref(false)
  const bindOnEnd = () => {
    recognition.onend = () => { isRecording.value = false }
  }
  bindOnEnd()

  const setLang = (newLang: string) => {
    if (storedOptions.lang === newLang) return
    if (isRecording.value) {
      try { recognition.stop() } catch { /* ignore */ }
      isRecording.value = false
    }
    recognition = rebuildInstance({ ...storedOptions, lang: newLang })
    bindOnEnd()
  }

  const start = (callback?: (result: string) => void) => { /* 同现有，用 recognition */ }
  const stop = () => { /* 同现有 */ }

  return { isRecording, start, stop, setLang }
}
```

- [ ] **Step 3:** 删除旧的「仅首次创建、忽略后续 options」逻辑（原 `getInstance` 第 17–26 行行为）。

- [ ] **Step 4:** 验证

1. 默认 `zh-CN` 说中文可识别
2. 调用 `setLang('en-US')` 后说英文可识别
3. 录音中切 lang 应先 stop 再重建，不抛错

---

## Phase 1 — 五轨道并行

> 可多人/多 agent 并行；合并顺序建议：0 → D(oral UI) → A → B → C → E。

---

### 轨道 A — F4 RecommendCard 直达

**Files:**
- Modify: `apps/web/src/components/RecommendCard.vue`
- Modify: `apps/web/src/views/Home/index.vue`
- Modify: `apps/web/src/views/Course/index.vue`（若课程页也展示 RecommendCard）

- [ ] **Step 1:** `RecommendCard.vue` 模板中课程列表区域替换为：

```vue
<CourseRecommendList
  :courses="data.courses"
  @buy="(c) => emit('buy', c)"
  @learn="(c) => emit('learn', c)"
/>
```

删除 `handleStartLearn` 内 `router.push('/courses/index')`。

添加：`defineEmits<{ buy: [CourseBatchStatus]; learn: [CourseBatchStatus] }>()`

- [ ] **Step 2:** `Home/index.vue`

```vue
<!-- 已有 RecommendCard -->
<RecommendCard compact @buy="onRecommendBuy" @learn="onRecommendLearn" />
<CoursePay v-model="payVisible" :course="selectedCourse" @success="onPaySuccess" />

<script>
import CoursePay from '@/views/Course/components/Pay.vue'
import { useCourseAction } from '@/hooks/useCourseAction'
const { goLearn, toCourse } = useCourseAction()
const onRecommendBuy = (c) => { selectedCourse.value = toCourse(c); payVisible.value = true }
const onRecommendLearn = (c) => goLearn(c)
</script>
```

- [ ] **Step 3:** Hero「查看课程」按钮加 `@click="router.push('/courses/index')"`

- [ ] **Step 4:** 验证：首页推荐 → 未购弹 Pay → 已购进学习页

---

### 轨道 B — F5 聊天内推荐购课

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatMessage.vue`
- Modify: `apps/web/src/views/Chat/index.vue`
- Modify: `server/ai/services/recommendation.py`

- [ ] **Step 1:** `ChatMessage.vue` — tool 区块扩展

当 `item.type === 'tool' && item.toolName === 'course_recommendation' && item.toolOutput`：

```ts
const recommendData = computed(() => {
  try {
    return JSON.parse(props.item.toolOutput!)
  } catch { return null }
})
```

模板：展开 tool 时渲染 `CourseRecommendList`，事件 `@buy` / `@learn` 向 ChatArea 冒泡（ChatMessage emit）。

- [ ] **Step 2:** `ChatArea.vue` 转发 emit 到父级；`Chat/index.vue` 接 Pay（同轨道 A 模式）

- [ ] **Step 3:** `recommendation.py` 添加后处理：

```python
async def _normalize_course_ids(db, courses: list[dict]) -> list[dict]:
    # 校验 course_id 存在于 DB；否则按 title 模糊匹配 Course.name
    # 仍失败则 course_id = None
```

在 `get_recommendation` 返回前调用。

- [ ] **Step 4:** 验证：normal 聊天输入「帮我推荐课程」→ 工具卡片 → 购买/学习按钮可用

---

### 轨道 C — F1 TTS 朗读

**Files:**
- Create: `apps/web/src/hooks/useTTS.ts`
- Modify: `apps/web/src/views/Chat/components/ChatMessage.vue`
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1:** `useTTS.ts`

```ts
export function useTTS() {
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window
  const isSpeaking = ref(false)

  function stripForSpeech(htmlOrMd: string): string {
    return htmlOrMd.replace(/<[^>]+>/g, '').replace(/[*#`_]/g, '').trim()
  }

  function speak(text: string, lang = 'zh-CN') {
    if (!supported || !text) return
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(stripForSpeech(text))
    u.lang = lang
    u.onend = () => { isSpeaking.value = false }
    isSpeaking.value = true
    window.speechSynthesis.speak(u)
  }

  function stop() {
    window.speechSynthesis.cancel()
    isSpeaking.value = false
  }

  return { supported, isSpeaking, speak, stop, stripForSpeech }
}
```

- [ ] **Step 2:** `ChatMessage.vue` AI 卡片 footer 加朗读按钮；emit 可选

- [ ] **Step 3:** Props: `autoTts?: boolean`, `ttsLang?: string`

- [ ] **Step 4:** `watch(() => item.streaming, (v, ov) => { if (ov && !v && autoTts) speak once per message id })`

- [ ] **Step 5:** `ChatArea.vue` 传入：

```ts
:auto-tts="['oral','master'].includes(chatStore.activeRole)"
:tts-lang="chatStore.activeRole === 'oral' || chatStore.activeRole === 'master' ? 'en-US' : 'zh-CN'"
```

- [ ] **Step 6:** 验证：master 回复完成后自动朗读；点 🔊 可重复；新消息打断旧朗读

---

### 轨道 D — F2 口语角色 oral

**Files:**
- Modify: `server/ai/services/prompt.py`
- Modify: `server/ai/services/tools/__init__.py`
- Modify: `server/ai/services/chat.py`
- Modify: `apps/web/src/views/Chat/roleConfig.ts`
- Modify: `apps/web/src/views/Chat/index.vue`
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

**前置:** Task 0.5 `setLang` 已完成。

- [ ] **Step 1:** `prompt.py` 追加 CHAT_MODES 项（prompt 全文见设计文档 F2）

- [ ] **Step 2:** `tools/__init__.py`

```python
def make_tools_by_role(user_id: str, role: str) -> list:
    if role == "normal":
        return make_tools(user_id)
    if role == "oral":
        return [grammar_check]
    return []
```

- [ ] **Step 3:** `chat.py` 第 95 行改为：

```python
tools = make_tools_by_role(user_id, role)
```

`_agent_cache_key` **无需修改** — `oral` 自动走 `(oral, deep_think)` 缓存。

- [ ] **Step 4:** `roleConfig.ts` 新增 `oral` 条目（theme 建议 teal/cyan 系，icon 🎙️，cards 3 个场景占位）

- [ ] **Step 5:** `Chat/index.vue` VALID_ROLES 加 `'oral'`

- [ ] **Step 6:** `ChatArea.vue` 接 Task 0.5 的 `setLang`

```ts
import { watch, computed } from 'vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const voiceLang = computed(() =>
  chatStore.activeRole === 'oral' ? 'en-US' : 'zh-CN'
)

const { isRecording, start, stop, setLang } = useVoiceToText({
  lang: voiceLang.value,
  continuous: true,
})

watch(
  voiceLang,
  (lang) => setLang(lang),
  { immediate: true },
)
```

说明：`immediate: true` 保证进入 Chat 页 / 切换角色时立刻更新识别语言；**不采用方案 B**（仅 watch 不改 hook）。

- [ ] **Step 7:** 验证

1. 左侧出现「口语考官」
2. 切换到 oral 后按住麦克风说英文 → 输入框为英文 transcript
3. 切回 normal → 中文识别恢复
4. grammar 工具可被调用

---

### 轨道 E — F3 首页看板 + 导出

#### Task E.1: 后端 dashboard API

**Files:**
- Create: `server/app/services/dashboard.py`
- Modify: `server/app/routers/user.py`
- Modify: `packages/common/user/index.ts`
- Modify: `apps/web/src/apis/user/index.ts`

- [ ] **Step 1:** `dashboard.py` 实现函数 `get_dashboard_stats(db, user_id)`：

| 字段 | 实现要点 |
|------|----------|
| `overview.checkInDays` | `User.day_number` |
| `overview.masteredWords` | count WordBookRecord is_master |
| `overview.purchasedCourses` | count CourseRecord purchased |
| `overview.wordsThisWeek` | WordBookRecord created_at >= now-7d |
| `wordTrend` | 按日 group by created_at（近 7 天） |
| `courseProgress` | 已购课程 + 按 Course.value 统计掌握词数/总量 |
| `activity.pvTrend` | `page_view JOIN visitor ON visitor.user_id = :uid` 近 7 天 |
| `activity.topPaths` | 同上 group by path limit 5 |
| `activity.totalPv` | 同上 count |

- [ ] **Step 2:** `user.py` 添加：

```python
@router.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.dashboard import get_dashboard_stats
    data = await get_dashboard_stats(db, user["userId"])
    return {"data": data, "code": 200, "message": "查询成功"}
```

- [ ] **Step 3:** 前端类型 + `getDashboard()` API

- [ ] **Step 4:** curl 验证返回 JSON 结构完整

#### Task E.2: 前端看板 + ECharts + 导出

**Files:**
- Create: `apps/web/src/views/Home/components/LearningDashboard.vue`
- Create: `apps/web/src/hooks/useDashboardExport.ts`
- Modify: `apps/web/src/views/Home/index.vue`
- Modify: `apps/web/package.json`

- [ ] **Step 1:** 安装依赖

```bash
cd apps/web && pnpm add echarts html2canvas jspdf
```

- [ ] **Step 2:** `LearningDashboard.vue`

- 根元素 `id="learning-dashboard"`
- 标题「我的学习数据」+ 按钮「导出 PNG」「导出 PDF」（class `data-export-hide`）
- 4 个概览 stat 卡片
- 两个 `ref` chart 容器，动态 `import('echarts')` 初始化折线图
- 课程进度 `el-progress` 列表
- Top paths 简单 table
- `onMounted` → `getDashboard()`

- [ ] **Step 3:** `useDashboardExport.ts`

```ts
export async function exportPng(el: HTMLElement, filename: string) {
  const html2canvas = (await import('html2canvas')).default
  hideExportButtons(el, true)
  const canvas = await html2canvas(el, { scale: 2, useCORS: true })
  hideExportButtons(el, false)
  canvas.toBlob(blob => { /* download */ })
}

export async function exportPdf(el: HTMLElement, filename: string) {
  const [html2canvas, { jsPDF }] = await Promise.all([
    import('html2canvas').then(m => m.default),
    import('jspdf'),
  ])
  // 截图 → 按 A4 高度分页 addImage
}
```

- [ ] **Step 4:** `Home/index.vue` RecommendCard 下方：

```vue
<LearningDashboard v-if="userStore.getUser" class="mt-6" />
```

- [ ] **Step 5:** 验证：登录首页可见图表；导出 PNG/PDF 文件可打开

---

## Phase 2 — 联调打磨

### Task 2.1: Tracker 自定义事件

**Files:**
- Modify: `apps/tracker/index.ts`
- Modify: `apps/web/src/App.vue` 或各触发点

- [ ] **Step 1:** Tracker 类增加：

```ts
public async trackEvent(type: string, payload?: Record<string, unknown>) {
  await this.init()
  if (!this.visitorId) return
  await reportFetch(this.config.baseUrl + this.config.event.api, {
    visitorId: this.visitorId,
    event: type,
    payload,
    url: location.href,
  })
}
```

- [ ] **Step 2:** 暴露 tracker 实例（App.vue export 或 composable `useTracker()`）

- [ ] **Step 3:** 触发点

| 事件 | 文件 |
|------|------|
| `check_in` | Home 打卡成功 |
| `pay_success` | Pay.vue showPaySuccess |
| `course_learn_start` | Learn/index.vue onMounted |

- [ ] **Step 4:** 看板 `topPaths` / 事件统计有数据（或仍显示暂无）

### Task 2.2: 导出与空态

- [ ] 无数据时图表显示「暂无数据」，仍可导出
- [ ] PDF 长图分页不截断图表
- [ ] 导出时隐藏 `data-export-hide` 元素

### Task 2.3: 全流程冒烟

按下方检查清单逐项勾选。

---

## 依赖关系

```
Phase 0.1 oral types
Phase 0.2 batch-status API
Phase 0.3 CourseRecommendList + useCourseAction
Phase 0.5 useVoiceToText setLang  ← oral 前置
        │
        ├── 轨道 A (F4 RecommendCard + Home Pay)
        ├── 轨道 B (F5 Chat tool cards + Chat Pay)
        ├── 轨道 C (F1 TTS) ── 可与 D 联调
        ├── 轨道 D (F2 oral) ── 依赖 0.1
        └── 轨道 E (F3 dashboard) ── 独立后端+Home UI
Phase 2 埋点 + 导出 + 冒烟
```

---

## 冒烟检查清单

| # | 步骤 | 预期 |
|---|------|------|
| 1 | 登录打开首页 | RecommendCard 下出现「我的学习数据」 |
| 2 | 点击导出 PNG | 下载 PNG，含概览与图表 |
| 3 | 点击导出 PDF | 下载 PDF，内容完整 |
| 4 | 聊天 normal「推荐课程」 | 工具区出现课程卡片与价格 |
| 5 | 未购课点「立即购买」 | Pay 弹窗 → 支付宝新标签 |
| 6 | 已购课点「立即学习」 | 进入 `/courses/learn/...` |
| 7 | 首页 RecommendCard 同逻辑 | 不进空课程列表 |
| 8 | 选 oral 角色 | 左侧有口语考官，语音默 en-US |
| 9 | oral/master 回复完成 | 自动朗读一次 |
| 10 | 任意 AI 消息点 🔊 | 手动朗读 |
| 11 | batch-status 无效 id | 不 404；该条无购买按钮 |
| 12 | 支付成功后刷新首页看板 | 已购课程数/进度更新 |

---

## 已知实现注意点

| 项 | 说明 |
|----|------|
| `useVoiceToText` | **Task 0.5 方案 A** 已定型：`setLang` + 重建实例；Track D Step 6 watch 调用 |
| `CourseRecommendation` | 已有于 `@/apis/recommend`；Task 0.3 Step 0 引用，不迁 packages/common |
| Tracker 无公开 track API | Phase 2 Task 2.1 先扩展 SDK |
| 无自动化测试 | 靠冒烟清单 + 手动 curl |
| 托福 ¥80000 | 不改价；答辩说明沙箱演示价 |
| oral agent 缓存 | 允许缓存，与 master 相同 |

---

## 不在本期

- 独立 `/dashboard` 路由
- 付费 TTS / 发音打分
- ClickHouse
- 管理后台
- 修改 seed 托福价格

---

## 建议提交粒度（可选）

| 提交 | 范围 |
|------|------|
| 1 | Phase 0 全部 |
| 2 | 轨道 D oral |
| 3 | 轨道 A + B 推荐购课 |
| 4 | 轨道 C TTS |
| 5 | 轨道 E 看板 + 导出 |
| 6 | Phase 2 埋点 + 文档 |

---

**执行口令:** 用户审阅本 plan 无误后回复「开始执行」，从 **Phase 0 Task 0.1 Step 1** 起实施。

# AI 课程推荐与个性化学习计划 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为英语学习平台新增 AI 驱动的课程推荐和个性化学习计划功能，支持聊天工具和页面卡片两种交互方式。

**Architecture:** 推荐逻辑集中在 `ai/services/recommendation.py`，AI 工具和 REST 端点共用。LLM 生成结构化 JSON 推荐结果，进程内字典缓存 24 小时。冷启动用户返回默认推荐。

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy async, LangChain/DeepSeek, Vue 3, TypeScript, Tailwind CSS 4, Element Plus

---

## 文件结构

### 新增文件

| 文件 | 职责 |
|------|------|
| `server/ai/services/recommendation.py` | 推荐服务核心：数据查询 + LLM 调用 + 缓存 + 冷启动处理 |
| `server/ai/services/tools/recommend.py` | AI 工具定义：`make_course_recommendation(user_id)` 工厂函数 |
| `server/ai/routers/recommend.py` | REST 端点：`GET /ai/v1/recommend` |
| `apps/web/src/apis/recommend/index.ts` | 前端 API 调用封装 |
| `apps/web/src/components/RecommendCard.vue` | 推荐卡片组件 |

### 修改文件

| 文件 | 修改内容 |
|------|------|
| `server/ai/services/tools/__init__.py` | `make_tools()` 新增 `course_recommendation` |
| `server/ai/main.py` | 注册 recommend 路由 |
| `apps/web/src/views/Home/index.vue` | 引入精简版推荐卡片 |
| `apps/web/src/views/Course/index.vue` | 引入完整版推荐卡片 |

---

## Task 1: 推荐服务核心 — `recommendation.py`

**Files:**
- Create: `server/ai/services/recommendation.py`

- [ ] **Step 1: 创建推荐服务文件，实现数据查询函数**

```python
# server/ai/services/recommendation.py
"""AI 课程推荐与个性化学习计划服务。"""
import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.user import User
from app.models.word_book import WordBook, WordBookRecord
from app.models.course import Course, CourseRecord
from ai.services.llm import get_llm

logger = logging.getLogger(__name__)

# 进程内缓存：{user_id: {data, generated_at}}
_recommend_cache: dict[str, dict] = {}

# 缓存过期时间（秒）
CACHE_TTL = 24 * 60 * 60

# 课程类型白名单（与 learn service 一致）
VALID_COURSE_TYPES = {"gk", "zk", "gre", "toefl", "ielts", "cet6", "cet4", "ky"}

# 冷启动默认推荐
DEFAULT_RECOMMENDATION = {
    "courses": [
        {
            "course_id": None,
            "title": "大学英语四级单词",
            "reason": "CET4 是最基础的英语考试，适合所有学习者起步",
            "match_score": 1.0,
        }
    ],
    "daily_plan": {
        "new_words_per_day": 20,
        "review_frequency": "每3天复习一次",
        "estimated_completion": "约3个月",
    },
    "summary": "欢迎开始英语学习之旅！建议从 CET4 基础词汇开始，循序渐进。",
}


async def _query_user_data(db: AsyncSession, user_id: str) -> dict | None:
    """查询用户学习数据，返回 None 表示用户不存在。"""
    # 查询用户基本信息
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return None

    word_number = user.word_number or 0
    day_number = user.day_number or 0

    # 查询最近学习时间
    last_learn_result = await db.execute(
        select(func.max(WordBookRecord.created_at)).where(
            WordBookRecord.user_id == user_id
        )
    )
    last_learn_at = last_learn_result.scalar()
    if last_learn_at:
        last_learn_days = (datetime.now(timezone.utc) - last_learn_at.replace(tzinfo=timezone.utc)).days
    else:
        last_learn_days = -1  # 从未学习过

    # 查询各类别已掌握单词数
    category_mastered = {}
    for course_type in VALID_COURSE_TYPES:
        count_result = await db.execute(
            select(func.count(WordBookRecord.id))
            .join(WordBook, WordBookRecord.word_id == WordBook.id)
            .where(
                WordBookRecord.user_id == user_id,
                WordBookRecord.is_master.is_(True),
                getattr(WordBook, course_type).is_(True),
            )
        )
        category_mastered[course_type] = count_result.scalar() or 0

    # 查询各类别总单词数
    category_total = {}
    for course_type in VALID_COURSE_TYPES:
        count_result = await db.execute(
            select(func.count(WordBook.id)).where(
                getattr(WordBook, course_type).is_(True)
            )
        )
        category_total[course_type] = count_result.scalar() or 0

    # 查询已购课程
    purchased_result = await db.execute(
        select(Course)
        .join(CourseRecord, CourseRecord.course_id == Course.id)
        .where(
            CourseRecord.user_id == user_id,
            CourseRecord.is_purchased.is_(True),
        )
    )
    purchased_courses = purchased_result.scalars().all()

    # 查询所有课程
    all_courses_result = await db.execute(select(Course))
    all_courses = all_courses_result.scalars().all()

    return {
        "user": user,
        "word_number": word_number,
        "day_number": day_number,
        "last_learn_days": last_learn_days,
        "category_mastered": category_mastered,
        "category_total": category_total,
        "purchased_courses": purchased_courses,
        "all_courses": all_courses,
    }
```

- [ ] **Step 2: 实现 Prompt 构建和 LLM 调用**

在 `server/ai/services/recommendation.py` 末尾追加：

```python
def _build_prompt(user_data: dict) -> str:
    """构建推荐 Prompt。"""
    word_number = user_data["word_number"]
    day_number = user_data["day_number"]
    last_learn_days = user_data["last_learn_days"]
    category_mastered = user_data["category_mastered"]
    category_total = user_data["category_total"]
    purchased_courses = user_data["purchased_courses"]
    all_courses = user_data["all_courses"]

    # 活跃度描述
    if last_learn_days == -1:
        active_desc = "从未学习过"
    elif last_learn_days == 0:
        active_desc = "今天已学习"
    else:
        active_desc = f"{last_learn_days}天前学习"

    # 各类别掌握度
    category_lines = []
    for ct in VALID_COURSE_TYPES:
        mastered = category_mastered.get(ct, 0)
        total = category_total.get(ct, 0)
        if total > 0:
            rate = round(mastered / total * 100, 1)
            category_lines.append(f"- {ct.upper()}: {rate}%（{mastered}/{total}）")

    # 已购课程
    purchased_ids = {c.id for c in purchased_courses}
    purchased_lines = []
    for course in purchased_courses:
        ct = course.value
        mastered = category_mastered.get(ct, 0)
        total = category_total.get(ct, 0)
        progress = round(mastered / total * 100, 1) if total > 0 else 0
        purchased_lines.append(f"- {course.name} (进度: {progress}%)")

    # 未购课程
    unpurchased_lines = []
    for course in all_courses:
        if course.id not in purchased_ids:
            unpurchased_lines.append(f"- [{course.id}] {course.name} - {course.description or '暂无描述'}")

    prompt = f"""你是一个英语学习顾问。根据以下用户数据生成推荐：

【用户画像】
- 已掌握单词：{word_number}
- 打卡天数：{day_number}
- 学习活跃度：{active_desc}

【各类别掌握度】
{chr(10).join(category_lines) if category_lines else "- 暂无学习数据"}

【已购课程】（进度 = 该课程类别下已掌握单词数 / 该类别总单词数 × 100%）
{chr(10).join(purchased_lines) if purchased_lines else "- 暂无已购课程"}

【未购课程】
{chr(10).join(unpurchased_lines) if unpurchased_lines else "- 暂无未购课程"}

请输出 JSON 格式的推荐结果，包含 courses（1-2 个推荐）和 daily_plan。
courses 中每个元素包含: course_id（如果是未购课程则填写对应 id，已购课程填 null）、title、reason、match_score（0-1）。
daily_plan 包含: new_words_per_day、review_frequency、estimated_completion。
另外包含 summary 字段，用一句话总结推荐理由。

只输出 JSON，不要输出其他内容。"""

    return prompt


def _parse_llm_output(raw: str) -> dict:
    """解析 LLM 输出的 JSON，带容错。"""
    # 1. 直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. 提取 ```json ... ``` 代码块
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 降级返回默认推荐
    logger.warning(f"LLM 输出 JSON 解析失败，使用默认推荐。原始输出: {raw[:200]}")
    return DEFAULT_RECOMMENDATION
```

- [ ] **Step 3: 实现缓存和主入口函数**

在 `server/ai/services/recommendation.py` 末尾追加：

```python
def _get_cached(user_id: str) -> dict | None:
    """获取缓存的推荐结果，过期返回 None。"""
    cached = _recommend_cache.get(user_id)
    if not cached:
        return None
    elapsed = (datetime.now(timezone.utc) - cached["generated_at"]).total_seconds()
    if elapsed > CACHE_TTL:
        del _recommend_cache[user_id]
        return None
    return cached["data"]


def _set_cache(user_id: str, data: dict):
    """设置缓存。"""
    _recommend_cache[user_id] = {
        "data": data,
        "generated_at": datetime.now(timezone.utc),
    }


def clear_cache(user_id: str):
    """清除指定用户的缓存。"""
    _recommend_cache.pop(user_id, None)


async def get_recommendation(user_id: str, force: bool = False) -> dict:
    """获取推荐结果。force=True 时强制刷新。"""
    # 检查缓存
    if not force:
        cached = _get_cached(user_id)
        if cached:
            return {**cached, "cached": True}

    # 查询用户数据
    async with async_session() as db:
        user_data = await _query_user_data(db, user_id)

    if not user_data:
        return {**DEFAULT_RECOMMENDATION, "cached": False, "generated_at": None}

    # 冷启动判断
    if user_data["word_number"] == 0 and user_data["day_number"] == 0:
        result = {**DEFAULT_RECOMMENDATION, "cached": False}
        _set_cache(user_id, result)
        return result

    # 构建 prompt 并调用 LLM
    prompt = _build_prompt(user_data)
    llm = get_llm(deep_think=False)

    try:
        response = await llm.ainvoke(prompt)
        raw_output = response.content
        parsed = _parse_llm_output(raw_output)
    except Exception as e:
        logger.error(f"推荐 LLM 调用失败: {e}")
        parsed = DEFAULT_RECOMMENDATION

    result = {
        "courses": parsed.get("courses", []),
        "daily_plan": parsed.get("daily_plan", {}),
        "summary": parsed.get("summary", ""),
        "cached": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    _set_cache(user_id, result)
    return result
```

- [ ] **Step 4: 验证文件语法正确**

Run: `cd server && python -c "import ast; ast.parse(open('ai/services/recommendation.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add server/ai/services/recommendation.py
git commit -m "feat: add recommendation service with LLM-based course suggestions"
```

---

## Task 2: AI 工具 — `recommend.py`

**Files:**
- Create: `server/ai/services/tools/recommend.py`

- [ ] **Step 1: 创建工具文件**

```python
# server/ai/services/tools/recommend.py
import json
from langchain_core.tools import tool
from ai.services.recommendation import get_recommendation


def make_course_recommendation(user_id: str):
    """返回绑定了 user_id 的 course_recommendation 工具"""

    @tool
    async def course_recommendation() -> str:
        """根据用户学习数据推荐课程和制定学习计划。
        当用户询问推荐课程、学习计划、下一步学什么、帮我规划学习时使用。"""
        result = await get_recommendation(user_id)
        return json.dumps(result, ensure_ascii=False)

    return course_recommendation
```

- [ ] **Step 2: 验证文件语法正确**

Run: `cd server && python -c "import ast; ast.parse(open('ai/services/tools/recommend.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add server/ai/services/tools/recommend.py
git commit -m "feat: add course_recommendation AI tool"
```

---

## Task 3: 注册工具到 `make_tools()`

**Files:**
- Modify: `server/ai/services/tools/__init__.py`

- [ ] **Step 1: 更新 `__init__.py`**

```python
# server/ai/services/tools/__init__.py
from .word import word_lookup
from .search import web_search
from .grammar import grammar_check
from .progress import make_progress_query
from .recommend import make_course_recommendation

# 保留 base_tools 用于非用户相关场景（如测试）
base_tools = [word_lookup, web_search, grammar_check]


def make_tools(user_id: str) -> list:
    """创建绑定用户 ID 的工具列表"""
    progress_query = make_progress_query(user_id)
    course_recommendation = make_course_recommendation(user_id)
    return [word_lookup, web_search, grammar_check, progress_query, course_recommendation]
```

- [ ] **Step 2: 验证导入正确**

Run: `cd server && python -c "from ai.services.tools import make_tools; tools = make_tools('test'); print(f'{len(tools)} tools: {[t.name for t in tools]}')"`
Expected: `5 tools: ['word_lookup', 'web_search', 'grammar_check', 'progress_query', 'course_recommendation']`

- [ ] **Step 3: Commit**

```bash
git add server/ai/services/tools/__init__.py
git commit -m "feat: register course_recommendation tool in make_tools()"
```

---

## Task 4: REST 端点 — `recommend.py` 路由

**Files:**
- Create: `server/ai/routers/recommend.py`

- [ ] **Step 1: 创建路由文件**

```python
# server/ai/routers/recommend.py
from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from ai.services.recommendation import get_recommendation, clear_cache

router = APIRouter(prefix="/ai/v1/recommend", tags=["recommend"])


@router.get("")
async def recommend(
    force: bool = Query(default=False, description="强制刷新推荐"),
    user: dict = Depends(get_current_user),
):
    """获取 AI 课程推荐与学习计划。"""
    user_id = user["userId"]

    if force:
        clear_cache(user_id)

    result = await get_recommendation(user_id, force=force)
    return result
```

- [ ] **Step 2: 验证文件语法正确**

Run: `cd server && python -c "import ast; ast.parse(open('ai/routers/recommend.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add server/ai/routers/recommend.py
git commit -m "feat: add GET /ai/v1/recommend endpoint"
```

---

## Task 5: 注册路由到 `main.py`

**Files:**
- Modify: `server/ai/main.py:16` (import) 和 `server/ai/main.py:52-54` (注册路由)

- [ ] **Step 1: 更新 import**

将 `server/ai/main.py` 第 16 行：
```python
from ai.routers import prompt, chat, conversation
```
改为：
```python
from ai.routers import prompt, chat, conversation, recommend
```

- [ ] **Step 2: 注册路由**

在 `server/ai/main.py` 第 54 行后追加：
```python
ai_app.include_router(recommend.router)
```

- [ ] **Step 3: 验证应用启动**

Run: `cd server && python -c "from ai.main import ai_app; routes = [r.path for r in ai_app.routes]; print('/ai/v1/recommend' in routes)"`
Expected: `True`

- [ ] **Step 4: Commit**

```bash
git add server/ai/main.py
git commit -m "feat: register recommend router in ai_app"
```

---

## Task 6: 前端 API 封装

**Files:**
- Create: `apps/web/src/apis/recommend/index.ts`

- [ ] **Step 1: 创建 API 文件**

```typescript
// apps/web/src/apis/recommend/index.ts
import { aiApi, type Response } from '..';

export interface CourseRecommendation {
    course_id: string | null;
    title: string;
    reason: string;
    match_score: number;
}

export interface DailyPlan {
    new_words_per_day: number;
    review_frequency: string;
    estimated_completion: string;
}

export interface RecommendData {
    courses: CourseRecommendation[];
    daily_plan: DailyPlan;
    summary: string;
    cached: boolean;
    generated_at: string | null;
}

export const getRecommend = (force = false) =>
    aiApi.get('/recommend', { params: { force } }) as Promise<Response<RecommendData>>;
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/apis/recommend/index.ts
git commit -m "feat: add recommend API client"
```

---

## Task 7: 推荐卡片组件 — `RecommendCard.vue`

**Files:**
- Create: `apps/web/src/components/RecommendCard.vue`

- [ ] **Step 1: 创建组件**

```vue
<!-- apps/web/src/components/RecommendCard.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getRecommend, type RecommendData } from '@/apis/recommend';

const props = defineProps<{
    /** 精简模式（首页用） */
    compact?: boolean;
}>();

const router = useRouter();
const loading = ref(true);
const data = ref<RecommendData | null>(null);
const error = ref(false);

const fetchRecommend = async (force = false) => {
    loading.value = true;
    error.value = false;
    try {
        const res = await getRecommend(force);
        data.value = res.data;
    } catch {
        error.value = true;
    } finally {
        loading.value = false;
    }
};

const handleRefresh = () => fetchRecommend(true);

const handleStartLearn = (courseId: string | null) => {
    if (courseId) {
        router.push({ path: '/course', query: { id: courseId } });
    } else {
        router.push('/course');
    }
};

onMounted(() => fetchRecommend());
</script>

<template>
    <!-- 加载中 -->
    <div v-if="loading" class="bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm animate-pulse">
        <div class="h-5 bg-zinc-200 rounded w-32 mb-4"></div>
        <div class="h-4 bg-zinc-100 rounded w-full mb-2"></div>
        <div class="h-4 bg-zinc-100 rounded w-3/4"></div>
    </div>

    <!-- 错误/无数据 -->
    <div v-else-if="error || !data" class="bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm text-center">
        <p class="text-zinc-400 text-sm">暂无推荐，请先开始学习</p>
    </div>

    <!-- 正常展示 -->
    <div v-else class="bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-semibold text-zinc-900">🎯 AI 学习推荐</h3>
            <button
                @click="handleRefresh"
                class="text-xs text-indigo-500 hover:text-indigo-600 transition-colors cursor-pointer"
            >
                换一批
            </button>
        </div>

        <!-- 推荐课程 -->
        <div v-for="course in data.courses" :key="course.title" class="mb-4 last:mb-0">
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <p class="text-sm font-medium text-zinc-800">{{ course.title }}</p>
                    <p class="text-xs text-zinc-500 mt-1">{{ course.reason }}</p>
                </div>
                <button
                    @click="handleStartLearn(course.course_id)"
                    class="ml-3 px-3 py-1 text-xs bg-indigo-500 text-white rounded-full hover:bg-indigo-600 transition-colors cursor-pointer shrink-0"
                >
                    开始学习
                </button>
            </div>
        </div>

        <!-- 学习计划（完整模式） -->
        <div v-if="!props.compact && data.daily_plan" class="mt-4 pt-4 border-t border-zinc-100">
            <p class="text-xs font-medium text-zinc-700 mb-2">📋 今日学习计划</p>
            <ul class="text-xs text-zinc-500 space-y-1">
                <li>· 每日新学 {{ data.daily_plan.new_words_per_day }} 个单词</li>
                <li>· {{ data.daily_plan.review_frequency }}</li>
                <li>· 预计 {{ data.daily_plan.estimated_completion }} 完成</li>
            </ul>
        </div>

        <!-- 总结 -->
        <p v-if="data.summary" class="text-xs text-zinc-400 mt-3 line-clamp-2">{{ data.summary }}</p>
    </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/components/RecommendCard.vue
git commit -m "feat: add RecommendCard component with loading/empty/normal states"
```

---

## Task 8: 首页集成精简版推荐卡片

**Files:**
- Modify: `apps/web/src/views/Home/index.vue`

- [ ] **Step 1: 在 Home 页面引入推荐卡片**

在 `apps/web/src/views/Home/index.vue` 的 `<script setup>` 中添加 import：
```typescript
import RecommendCard from '@/components/RecommendCard.vue';
```

在模板的合适位置（课程区域之前或欢迎区域之后）添加：
```vue
<!-- AI 推荐卡片 -->
<div v-if="userStore.getUser" class="mt-6">
    <RecommendCard compact />
</div>
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/views/Home/index.vue
git commit -m "feat: add compact RecommendCard to Home page"
```

---

## Task 9: 课程页集成完整版推荐卡片

**Files:**
- Modify: `apps/web/src/views/Course/index.vue`

- [ ] **Step 1: 在 Course 页面引入推荐卡片**

在 `apps/web/src/views/Course/index.vue` 的 `<script setup>` 中添加 import：
```typescript
import RecommendCard from '@/components/RecommendCard.vue';
```

在模板的 header 下方、tabs 上方添加：
```vue
<!-- AI 推荐卡片 -->
<div v-if="userStore.getUser" class="mb-8">
    <RecommendCard />
</div>
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/views/Course/index.vue
git commit -m "feat: add full RecommendCard to Course page"
```

---

## Task 10: 端到端验证

- [ ] **Step 1: 启动后端服务**

Run: `cd server && uv run python -m uvicorn ai.main:ai_app --port 3001 --reload`
Expected: 服务正常启动，无报错

- [ ] **Step 2: 测试冷启动推荐（新用户）**

使用 curl 或 Postman 调用 `GET /ai/v1/recommend`（需要 JWT token）。
Expected: 返回默认推荐（CET4 基础课程），`cached: false`

- [ ] **Step 3: 测试带学习数据的推荐**

用有学习记录的用户调用 `GET /ai/v1/recommend`。
Expected: 返回基于实际数据的 LLM 推荐结果

- [ ] **Step 4: 测试缓存**

再次调用同一用户的 `GET /ai/v1/recommend`。
Expected: 返回相同结果，`cached: true`

- [ ] **Step 5: 测试强制刷新**

调用 `GET /ai/v1/recommend?force=true`。
Expected: 返回新生成的结果，`cached: false`

- [ ] **Step 6: 测试 AI 工具触发**

在聊天中发送「推荐我学什么课程」。
Expected: AI 调用 `course_recommendation` 工具，返回推荐结果

- [ ] **Step 7: 启动前端验证页面卡片**

Run: `pnpm web`
Expected: 首页和课程页正常展示推荐卡片，「换一批」按钮可用

- [ ] **Step 8: Final Commit**

```bash
git add -A
git commit -m "feat: complete AI course recommendation and learning plan feature"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** 课程推荐 ✓、学习计划 ✓、冷启动 ✓、缓存 ✓、AI 工具 ✓、REST 端点 ✓、前端卡片 ✓
- [x] **Placeholder scan:** 无 TBD/TODO，所有代码完整
- [x] **Type consistency:** `get_recommendation()`, `_query_user_data()`, `_build_prompt()`, `_parse_llm_output()` 在所有任务中签名一致
- [x] **File paths:** 所有路径基于实际项目结构验证
- [x] **Code patterns:** 工厂函数模式与 `progress_query` 一致，路由模式与 `chat.py` 一致，API 封装与 `learn/index.ts` 一致

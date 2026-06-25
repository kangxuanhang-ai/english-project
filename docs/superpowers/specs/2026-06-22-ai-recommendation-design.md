# AI 课程推荐与个性化学习计划设计

## 概述

为英语学习平台新增 AI 驱动的课程推荐和个性化学习计划功能。基于用户现有学习数据（已掌握单词、打卡天数、课程购买记录），通过 LLM 生成个性化推荐。

## 目标

1. 用户在聊天中问「推荐课程」「我该学什么」时，AI 能给出个性化推荐
2. 首页和课程页展示 AI 推荐卡片，引导用户学习
3. 生成每日学习计划（学多少词、复习频率、预计完成时间）

## 方案选择

采用**方案 A：AI 工具 + 共享推荐服务**。推荐逻辑集中在 `ai/services/recommendation.py`，AI 工具和 REST 端点共用。

```
AI 工具 (chat)  ──┐
                   ├──▶  recommendation service  ──▶  LLM  ──▶  推荐结果
前端页面 (REST) ──┘
```

---

## 数据流与推荐逻辑

### 查询的用户数据

| 数据 | 来源 | 用途 |
|------|------|------|
| 已掌握单词总数 | `User.word_number` | 评估整体水平 |
| 打卡天数 | `User.day_number` | 评估学习习惯 |
| 各类别已掌握单词数 | `WordBookRecord` JOIN `WordBook`，按 `cet4/cet6/...` 分组统计 | 计算各类别掌握百分比 |
| 各类别总单词数 | `WordBook` 按标签统计 | 计算掌握百分比的分母 |
| 已购课程及进度 | `CourseRecord` + `Course` + `WordBookRecord` 计算：该课程类别下用户已掌握单词数 / 该类别总单词数。`Course.value` 直接对应 `WordBook` 的布尔字段（如 `value="cet4"` → `WordBook.cet4`），与 learn service 的 `getattr(WordBook, course_type)` 模式一致 | 判断已购课程完成度 |
| 最近学习记录 | `WordBookRecord.created_at` | 判断学习活跃度 |

### 冷启动处理

新用户（`word_number=0` 且 `day_number=0`）→ 跳过 LLM，直接返回默认推荐（CET4 基础课程）。

### 缓存策略

- 缓存实现：进程内字典（`dict[user_id, {data, generated_at}]`），与现有 LLM 实例缓存模式一致
- 缓存过期：24 小时（检查 `generated_at` 与当前时间差）
- `force=true` 时清除该用户的缓存条目并重新生成

### LLM 输出结构

LLM 输出严格 JSON 格式：

```json
{
  "courses": [
    {
      "course_id": "xxx",
      "title": "CET4 核心词汇",
      "reason": "你已掌握 85% 的 CET4 词汇，适合冲刺高分",
      "match_score": 0.92
    }
  ],
  "daily_plan": {
    "new_words_per_day": 20,
    "review_frequency": "每3天复习一次",
    "estimated_completion": "45天"
  },
  "summary": "你目前 CET4 掌握度较高，建议..."
}
```

### JSON 解析容错

1. 先 `json.loads(llm_output)`
2. 失败则提取 ` ```json ``` ` 代码块
3. 仍然失败则返回降级结果（默认推荐）

### Prompt 模板

```
你是一个英语学习顾问。根据以下用户数据生成推荐：

【用户画像】
- 已掌握单词：{word_number}
- 打卡天数：{day_number}
- 学习活跃度：{last_learn_days}天前学习

【各类别掌握度】
- CET4: {掌握率}%（{已掌握}/{总数}）
- CET6: {掌握率}%
- ...

【已购课程】（进度 = 该课程类别下已掌握单词数 / 该类别总单词数 × 100%）
- {course_name} (进度: {progress}%)

【未购课程】
- [{course_id}] {course_name} - {description}

请输出 JSON 格式的推荐结果，包含 courses（1-2 个推荐）和 daily_plan。
```

---

## AI 工具设计

新增工具 `course_recommendation`，加入 `normal` 角色的工具列表。

**工具定义：**
- 名称：`course_recommendation`
- 输入：无参数（`user_id` 通过闭包绑定，与 `progress_query` 同模式）
- 触发场景：用户问「推荐课程」「我该学什么」「制定学习计划」「帮我规划学习」等
- 输出：JSON 格式的推荐结果

**实现模式：** 与 `progress_query` 相同的工厂函数模式 `make_course_recommendation(user_id)`。

**工具列表更新：** `make_tools(user_id)` 返回 5 个工具（原来 4 个 + `course_recommendation`）。

---

## REST API 端点

新增 `ai/routers/recommend.py`。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/ai/v1/recommend?force=false` | 获取推荐结果。`force=true` 时清除缓存重新生成 |

**成功响应（200）：**
```json
{
  "timestamp": "...",
  "path": "/ai/v1/recommend",
  "message": "success",
  "code": 200,
  "success": true,
  "data": {
    "courses": [...],
    "daily_plan": {...},
    "summary": "...",
    "cached": true,
    "generated_at": "2026-06-22T10:00:00Z"
  }
}
```

**错误响应：** 走全局异常处理器，格式为 `{timestamp, path, message, code, success: false, data: null}`。

**认证：** 需要 JWT（从 header 提取 user_id）。

---

## 前端集成

### 推荐卡片组件

`apps/web/src/components/RecommendCard.vue`

**放置位置：**
- 首页（Home）：精简版，作为欢迎区域的一部分
- 课程页（Course）：完整版，顶部推荐区

**UI 状态：**
```vue
<!-- 加载中 -->
<RecommendCard loading />

<!-- 正常展示 -->
<RecommendCard :data="recommendData" />

<!-- 无推荐（极端情况） -->
<RecommendCard empty message="暂无推荐，请先开始学习" />
```

**交互：**
- 页面加载时：`GET /ai/v1/recommend`（默认 `force=false`，优先返回缓存）
- 点击「换一批」：`GET /ai/v1/recommend?force=true`
- 点击「开始学习」：跳转到对应课程的学习页面

### API 调用封装

`apps/web/src/apis/recommend/index.ts`

```typescript
export const getRecommend = (force = false) =>
  aiApi.get('/recommend', { params: { force } })
```

---

## 新增文件清单

### 后端（server/ai/）
| 文件 | 说明 |
|------|------|
| `services/recommendation.py` | 推荐服务核心逻辑（数据查询 + LLM 调用 + 缓存） |
| `services/tools/recommend.py` | AI 工具定义 |
| `routers/recommend.py` | REST API 端点 |

### 前端（apps/web/src/）
| 文件 | 说明 |
|------|------|
| `apis/recommend/index.ts` | API 调用封装 |
| `components/RecommendCard.vue` | 推荐卡片组件 |

### 修改文件
| 文件 | 修改内容 |
|------|------|
| `ai/services/tools/__init__.py` | `make_tools()` 新增 `course_recommendation` 工具 |
| `ai/main.py` | 注册 recommend 路由 |
| `apps/web/src/views/Home.vue` | 引入精简版推荐卡片 |
| `apps/web/src/views/Course.vue` | 引入完整版推荐卡片 |

---

## 约束与边界

- 推荐结果缓存 24 小时，避免频繁 LLM 调用
- 冷启动用户返回默认推荐，不调用 LLM
- LLM 输出强制 JSON 格式，解析失败时降级处理
- 推荐基于现有数据（word_number, day_number, CourseRecord），不新增数据追踪
- 仅 `normal` 角色可使用 `course_recommendation` 工具

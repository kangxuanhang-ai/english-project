# 答辩前优化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 Phase 1 后的 4 项答辩关键优化 — 支付幂等、Chat role 校验、ChatArea 流式快修、Agent 缓存。

**Architecture:** 分 4 个独立批次实施，每批次可单独验证和提交。安全项（批次 1-2）最先做；体验项（批次 3）其次；性能项（批次 4）最后。批次间无依赖，但建议按顺序执行以便 smoke test 递进。

**Tech Stack:** Python FastAPI, SQLAlchemy, LangGraph, Vue 3 Composition API, TypeScript

**设计文档:** [2026-06-24-pre-defense-optimization-design.md](../specs/2026-06-24-pre-defense-optimization-design.md)

**前置:** Phase 1 稳定性修复已完成（bcrypt、CORS、XSS、JWT、头像鉴权等）

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `server/app/services/pay.py` | Modify | 支付回调幂等逻辑 |
| `server/ai/routers/chat.py` | Modify | role 与 conversation 校验 + 强制覆盖 |
| `server/ai/schemas/chat.py` | Modify | role 改为 Literal 枚举 |
| `server/ai/services/chat.py` | Modify | Agent 缓存 dict |
| `packages/common/chat/index.ts` | Modify | ChatMessage 增加可选 `id` |
| `apps/web/src/views/Chat/components/ChatArea.vue` | Modify | stable key、expandedTools、scroll 节流 |
| `apps/web/src/views/Chat/components/ChatMessage.vue` | Modify | markdown computed |

---

## 批次一：支付回调幂等

### Task 1: 支付回调幂等逻辑

**Files:**
- Modify: `server/app/services/pay.py`

- [ ] **Step 1: 添加 IntegrityError 导入**

在文件顶部添加：

```python
from sqlalchemy.exc import IntegrityError
from app.models.course import CourseRecord  # 若尚未导入
```

确认 `CourseRecord` 和 `TradeStatus` 已导入。

- [ ] **Step 2: 在查到 payment 后增加已处理短路**

在 `handle_payment_notify` 中，`payment = result.scalar_one_or_none()` 之后、`payment.trade_no = trade_no` 之前插入：

```python
# 幂等：已处理过的订单直接返回 success
if payment.trade_status == TradeStatus.TRADE_SUCCESS:
    return True

# 只处理支付宝成功状态
if form_data.get("trade_status") != "TRADE_SUCCESS":
    logging.info(f"Ignore non-success trade_status: {form_data.get('trade_status')}")
    return False
```

- [ ] **Step 3: 解析 body 后校验 userId**

在 `body = json.loads(body_str)` 成功后添加：

```python
if body.get("userId") != payment.user_id:
    logging.warning(f"userId mismatch: body={body.get('userId')} payment={payment.user_id}")
    await db.rollback()
    return False
```

- [ ] **Step 4: 创建 CourseRecord 前检查是否已存在**

在 `db.add(course_record)` 之前添加：

```python
existing_record = await db.execute(
    select(CourseRecord).where(
        CourseRecord.user_id == body["userId"],
        CourseRecord.course_id == body["courseId"],
    )
)
if existing_record.scalar_one_or_none():
    # 已有课程记录，仅更新 payment 状态
    payment.trade_no = trade_no
    payment.trade_status = TradeStatus.TRADE_SUCCESS
    payment.send_pay_time = datetime.now()
    await db.commit()
    return True
```

- [ ] **Step 5: commit 时 IntegrityError 兜底**

将 `await db.commit()` 包裹为：

```python
try:
    await db.commit()
except IntegrityError:
    await db.rollback()
    logging.info(f"Duplicate course record for {body['userId']}/{body['courseId']}, treating as success")
    return True
```

- [ ] **Step 6: 验证**

1. 启动 server → 沙箱支付一门课程 → 确认 CourseRecord 创建
2. 用相同 notify 参数重放 POST `/api/v1/pay/notify` → 仍返回 `success`，CourseRecord 数量不变
3. 构造 `trade_status=TRADE_CLOSED` 的 notify → 返回 `failure`

- [ ] **Step 7: 提交**

```bash
git add server/app/services/pay.py
git commit -m "fix: add idempotency to payment notify handler"
```

---

## 批次二：Chat role 校验

### Task 2: ChatRequest role 枚举

**Files:**
- Modify: `server/ai/schemas/chat.py`

- [ ] **Step 1: 将 role 改为 Literal**

```python
from typing import Literal

class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    role: Literal['normal', 'master', 'business', 'qilinge', 'xiaoman'] = "normal"
    deepThink: bool = False
    webSearch: bool = False
    conversationId: str = Field(..., min_length=1)
```

- [ ] **Step 2: 验证**

发送 `role: "invalid"` → 422 Validation Error

---

### Task 3: Chat 路由 role 校验 + 强制覆盖

**Files:**
- Modify: `server/ai/routers/chat.py`

- [ ] **Step 1: 在查到 conversation 后增加校验**

在 `if not conversation:` 检查之后、`conversation.updated_at = func.now()` 之前插入：

```python
if data.role != conversation.role:
    raise HTTPException(status_code=400, detail="角色与对话不匹配")
```

- [ ] **Step 2: 强制使用 conversation.role**

将：

```python
chat_data = data.model_dump()
chat_data["userId"] = user["userId"]
```

改为：

```python
chat_data = data.model_dump()
chat_data["role"] = conversation.role  # 强制以 DB 为准
chat_data["userId"] = user["userId"]
```

- [ ] **Step 3: 验证**

1. 创建 master 对话 → 正常聊天 → OK
2. 用 curl/Postman 对 master 对话 POST `{ "role": "normal", ... }` → 400
3. normal 对话触发 tool 调用 → OK

- [ ] **Step 4: 提交**

```bash
git add server/ai/schemas/chat.py server/ai/routers/chat.py
git commit -m "fix: validate and enforce chat role against conversation"
```

---

## 批次三：ChatArea 流式快修

### Task 4: ChatMessage 类型增加 id

**Files:**
- Modify: `packages/common/chat/index.ts`

- [ ] **Step 1: 添加 id 字段**

在 `ChatMessage` 类型中增加：

```typescript
id?: string  // 消息唯一标识，用于 v-for :key
```

- [ ] **Step 2: 提交**

```bash
git add packages/common/chat/index.ts
git commit -m "feat: add optional id field to ChatMessage type"
```

---

### Task 5: ChatArea 稳定 key + expandedTools + scroll 节流

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 模板 :key 改为 item.id**

```vue
:key="item.id ?? index"
```

- [ ] **Step 2: expandedTools 改为 Record**

```typescript
const expandedTools = ref<Record<string, boolean>>({})

const toggleToolExpand = (toolId: string | undefined) => {
    if (!toolId) return
    expandedTools.value = {
        ...expandedTools.value,
        [toolId]: !expandedTools.value[toolId],
    }
}
```

模板 prop 改为：

```vue
:expanded="!!expandedTools[item.toolId ?? '']"
```

- [ ] **Step 3: scrollToBottom 用 rAF 节流（pendingForce 合并）**

```typescript
let scrollRafId: number | null = null
let pendingForce = false

function scrollToBottom(force = false) {
    if (force) pendingForce = true
    if (scrollRafId !== null) return  // 合并为一次 rAF，不用 cancel + 闭包 capture force
    scrollRafId = requestAnimationFrame(() => {
        scrollRafId = null
        const f = pendingForce
        pendingForce = false
        const el = chatRef.value?.parentElement?.parentElement
        if (!el) return
        if (!f) {
            const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150
            if (!isNearBottom) return
        }
        chatRef.value?.scrollIntoView({ behavior: 'smooth' })
    })
}
```

在 `onUnmounted` 中添加：

```typescript
if (scrollRafId !== null) cancelAnimationFrame(scrollRafId)
pendingForce = false
```

- [ ] **Step 4: 发送消息时分配 id**

在 `list.value.push` 用户消息和 AI 消息时：

```typescript
list.value.push({ id: `human-${Date.now()}`, role: 'human', content: msg, type: 'chat' })
list.value.push({ id: `ai-${Date.now()}`, role: 'ai', content: '', reasoning: '', status: 'loading', type: 'chat', originalContent: msg, streaming: true })
```

在 tool 消息 push 时：

```typescript
list.value.push({ id: `tool-${data.id}`, role: 'ai', content: '', type: 'tool', toolId: data.id, toolName: data.tool, toolInput: data.input })
```

- [ ] **Step 5: 验证**

1. normal 角色查词 → tool 消息插入后气泡不错位
2. 点击 tool 展开/折叠 → UI 立即响应
3. 长回复流式 → 滚动流畅，无明显卡顿

---

### Task 6: ChatMessage markdown computed

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatMessage.vue`

- [ ] **Step 1: 添加 computed**

```typescript
import { ref, computed } from 'vue'

const renderedHtml = computed(() => {
    if (props.item.streaming || !props.item.content) return ''
    return parseMarkdown(props.item.content)
})
```

- [ ] **Step 2: 模板改用 computed**

将：

```vue
<div v-else v-html="parseMarkdown(item.content)" />
```

改为：

```vue
<div v-else v-html="renderedHtml" />
```

- [ ] **Step 3: 验证**

历史消息加载 → markdown 正常渲染（代码块、列表等）

- [ ] **Step 4: 提交**

```bash
git add apps/web/src/views/Chat/components/ChatArea.vue apps/web/src/views/Chat/components/ChatMessage.vue
git commit -m "fix: stable message keys, reactive tool expand, throttled scroll"
```

---

## 批次四：Agent 缓存

> **安全约束：** `normal` 角色的 `progress_query` / `course_recommendation` 通过闭包绑定 `user_id`，**禁止缓存 normal**。仅缓存 `master` / `business` / `qilinge` / `xiaoman`（tools 为空）。

### Task 7: Agent 缓存实现

**Files:**
- Modify: `server/ai/services/chat.py`

- [ ] **Step 1: 添加缓存 dict 和 key 函数**

在模块顶部（checkpointer 变量附近）添加：

```python
_agent_cache: dict[tuple, object] = {}

def _agent_cache_key(role: str, deep_think: bool, web_search: bool) -> tuple | None:
    """web_search 时 prompt 动态变化；normal 有 per-user 闭包 tools — 均不缓存。"""
    if web_search:
        return None
    if role == "normal":
        return None  # make_tools(user_id) 闭包捕获 user_id，禁止共享 agent
    return (role, deep_think)
```

- [ ] **Step 2: 提取 agent 获取逻辑**

在 `stream_chat` 的 for attempt 循环内，将 `create_react_agent(...)` 替换为：

```python
tools = make_tools(user_id) if role == "normal" else []

cache_key = _agent_cache_key(role, deep_think, web_search)
if cache_key and cache_key in _agent_cache:
    agent = _agent_cache[cache_key]
else:
    agent = create_react_agent(
        model=model,
        tools=tools,
        checkpointer=checkpointer,
        prompt=SystemMessage(content=prompt),
    )
    if cache_key:
        _agent_cache[cache_key] = agent
```

注意：删除循环内原有的重复 `tools = make_tools(...)` 行，避免重复赋值。

- [ ] **Step 3: 验证**

1. **缓存生效**：`master` 角色连续发两条消息 → 第二条首 token 更快
2. **user_id 隔离**：用户 A 在 normal 查进度 → 看到 A 的数据；换用户 B 查进度 → 看到 B 的数据（非 A）
3. normal 角色 tool 调用（查词、进度、推荐）→ 功能正常
4. 开启 web_search → 功能正常
5. 切换 master / business / qilinge / xiaoman → 各角色正常回复
6. 开启 deepThink → 正常

- [ ] **Step 4: 提交**

```bash
git add server/ai/services/chat.py
git commit -m "perf: cache agent for tool-less roles only, never cache normal"
```

---

## 完成 — 答辩前 Smoke Test

所有 Task 完成后，运行完整验证：

```bash
pnpm all
```

### 验证清单

- [ ] 注册/登录正常
- [ ] normal 角色聊天 + tool 调用（查词）→ 流式流畅，tool 可展开
- [ ] master 角色聊天 → 英文回复，无 tool
- [ ] master 角色连续聊天 → 第二次响应更快（Agent 缓存）
- [ ] 用户 A、B 分别在 normal 查学习进度 → 数据不串号
- [ ] 5 角色切换 → accent 联动正常（若角色剧场已完成）
- [ ] 沙箱支付 → 课程解锁 → 重复 notify 不重复开课
- [ ] curl master 对话 role=normal → 400

### 答辩最低交付

批次 1-3（Task 1-6）为 **必须**；批次 4（Task 7）为 **建议**。

---

## 审批

- [ ] 实施计划确认
- [ ] 批准开始执行

**执行方式：** 用户确认本计划后，Agent 按 Task 1 → Task 7 顺序实施，每批次完成后汇报并等待确认（可选）。

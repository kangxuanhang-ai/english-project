# Chat 模块 11 条问题修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Chat 模块 11 条已确认问题（3 条 P0 + 8 条 P1），分三批按模块推进。

**Architecture:** 第一批改后端 done/error 事件 + 前端 SSE 容错和自动滚动；第二批改 UI 交互（语法高亮、工具详情、删除确认等）；第三批重构 Token 刷新逻辑为统一工具函数。

**Tech Stack:** Python FastAPI, LangGraph astream_events v2, Vue 3, TypeScript, fetch-event-source, highlight.js, marked-highlight, Element Plus

**Spec:** `docs/superpowers/specs/2026-06-14-chat-issues-fix-design.md`

---

## 第一批：SSE/流式（#1, #2, #3, #6, #11）

### Task 1: 后端 — done/error 事件 + run_id

**Files:**
- Modify: `server/ai/services/chat.py:49-149`

- [ ] **Step 1: 修改 `stream_chat` 函数 — done/error 事件 + run_id**

在 `stream_chat` 函数中做三处改动：
1. `on_tool_start` 和 `on_tool_end` 的 `call_id` 改用 `event.get("run_id", "")`
2. `on_tool_end` 的 yield 加上 `id` 字段
3. 整个 `for` 循环用 try/except 包裹，正常结束 yield done，异常结束 yield error

```python
async def stream_chat(data: dict):
    """
    SSE 流式聊天。
    对应 NestJS ChatService.streamCompletion。
    """

    role = data.get("role", "normal")
    content = data.get("content", "")
    deep_think = data.get("deepThink", False)
    web_search = data.get("webSearch", False)
    user_id = data.get("userId", "")
    conversation_id = data.get("conversationId", "")

    prompt_obj = get_prompt_by_role(role)
    if not prompt_obj:
        raise ValueError("模式不存在")

    prompt = prompt_obj["prompt"]

    if deep_think and web_search:
        web_search = False

    if web_search:
        search_results = await create_bocha_search(content)
        if search_results:
            prompt += f"""
请根据以下搜索结果回答问题（并且返回你参考的网站名称）：

{search_results}
"""

    model = get_llm(deep_think)

    for attempt in range(2):
        checkpointer = await get_checkpointer()
        tools = make_tools(user_id) if role == "normal" else []
        agent = create_react_agent(
            model=model,
            tools=tools,
            checkpointer=checkpointer,
            prompt=SystemMessage(content=prompt),
        )

        thread_id = conversation_id
        try:
            messages = [HumanMessage(content=content)]
            async for event in agent.astream_events(
                {"messages": messages},
                config={"configurable": {"thread_id": thread_id}},
                version="v2",
            ):
                kind = event.get("event")
                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = event.get("data", {}).get("input", "")
                    if isinstance(tool_input, dict):
                        tool_input = json.dumps(tool_input, ensure_ascii=False)
                    call_id = str(event.get("run_id", ""))  # 用 run_id 替代随机 UUID
                    yield f"data: {json.dumps({'type': 'tool', 'id': call_id, 'tool': tool_name, 'input': str(tool_input)}, ensure_ascii=False)}\n\n"
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    tool_output = event.get("data", {}).get("output", "")
                    call_id = str(event.get("run_id", ""))  # 同一个 tool call 的 run_id 一致
                    yield f"data: {json.dumps({'type': 'tool_result', 'id': call_id, 'tool': tool_name, 'output': str(tool_output)}, ensure_ascii=False)}\n\n"
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        reasoning = getattr(chunk, "additional_kwargs", {}).get(
                            "reasoning_content", ""
                        )
                        if reasoning:
                            yield f"data: {json.dumps({'content': reasoning, 'role': 'ai', 'type': 'reasoning'}, ensure_ascii=False)}\n\n"
                        content_text = chunk.content if hasattr(chunk, "content") else ""
                        if content_text:
                            yield f"data: {json.dumps({'content': content_text, 'role': 'ai', 'type': 'chat'}, ensure_ascii=False)}\n\n"
            # 流正常结束，发 done 事件
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            break
        except OperationalError as e:
            if attempt == 0:
                await reset_checkpointer()
            else:
                logger.error(f"stream_chat OperationalError: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': '数据库连接异常，请重试'}, ensure_ascii=False)}\n\n"
                return
        except ValueError as e:
            if attempt == 0 and "tool_calls" in str(e):
                try:
                    await checkpointer.adelete_thread(thread_id)
                except Exception:
                    pass
            else:
                logger.error(f"stream_chat ValueError: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': '对话数据异常，请重试'}, ensure_ascii=False)}\n\n"
                return
        except Exception as e:
            logger.error(f"stream_chat unexpected error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': '服务异常，请重试'}, ensure_ascii=False)}\n\n"
            return
```

- [ ] **Step 2: 删除未使用的 `uuid` 导入**

文件顶部的 `import uuid` 不再需要，删除它。

- [ ] **Step 3: 验证后端改动**

从 `server/` 目录运行：
```bash
cd server && uv run python -c "from ai.services.chat import stream_chat; print('import ok')"
```
Expected: `import ok`

- [ ] **Step 4: Commit**

```bash
git add server/ai/services/chat.py
git commit -m "feat(chat): add done/error events and use run_id for tool matching"
```

---

### Task 2: 前端类型 — ChatMessageType + ChatStatus + ChatSSEMessage + ChatMessage

**Files:**
- Modify: `packages/common/chat/index.ts`

- [ ] **Step 1: ChatMessageType 加 `'done' | 'error'`**

```typescript
export type ChatMessageType = 'reasoning' | 'chat' | 'tool' | 'tool_result' | 'done' | 'error'
```

- [ ] **Step 2: ChatStatus 加 `'error'`**

```typescript
export type ChatStatus = 'loading' | 'tool_calling' | 'tool_done' | 'error'
```

- [ ] **Step 3: ChatSSEMessage 加 `message` 字段**

```typescript
export type ChatSSEMessage = {
    type: ChatMessageType
    content?: string
    role?: ChatRole
    reasoning?: string
    id?: string
    tool?: string
    input?: string
    output?: string
    message?: string  // error 事件的错误信息
}
```

- [ ] **Step 4: ChatMessage 加 `originalContent` 字段**

```typescript
export type ChatMessage = {
    role: ChatRole
    content: string;
    reasoning?: string;
    type: ChatMessageType
    status?: ChatStatus
    toolId?: string
    toolName?: string
    toolInput?: string
    toolOutput?: string
    originalContent?: string  // 重试时用的原始用户消息
}
```

- [ ] **Step 2: Commit**

```bash
git add packages/common/chat/index.ts
git commit -m "feat(common): add originalContent field to ChatMessage type"
```

---

### Task 3: SSE 容错 — JSON try-catch（#3）

**Files:**
- Modify: `apps/web/src/apis/sse/index.ts:69-71`

- [ ] **Step 1: 给 `onmessage` 加 try-catch**

将第 69-71 行：
```typescript
onmessage: (event) => {
    callback?.(JSON.parse(event.data) as T)
},
```

改为：
```typescript
onmessage: (event) => {
    try {
        callback?.(JSON.parse(event.data) as T)
    } catch (e) {
        console.warn('SSE JSON parse error:', event.data, e)
    }
},
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/apis/sse/index.ts
git commit -m "fix(sse): add try-catch around JSON.parse in onmessage"
```

---

### Task 4: ChatArea — done/error 事件处理 + 删除轮询（#2, #6）

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 传入 error callback 替换 `undefined`**

将第 163-175 行的 `sse()` 调用中，第 5 个参数从 `undefined` 改为 error callback：

```typescript
sse<ChatSSEMessage, ChatDto>(CHAT_URL, "POST",
    { conversationId: chatStore.activeConversationId!, role: chatStore.activeRole, content: msg, deepThink: deepThink.value, webSearch: webSearch.value },
    (data) => {
        const aiMsg = list.value[aiIndex]
        if (!aiMsg) return
        if (data.type === 'reasoning') { aiMsg.reasoning += data.content ?? ''; if (aiMsg.status === 'loading') aiMsg.status = undefined }
        if (data.type === 'chat') { if (aiMsg.status) aiMsg.status = undefined; aiMsg.content += data.content ?? '' }
        if (data.type === 'tool') { toolCallingStart = Date.now(); aiMsg.status = 'tool_calling'; aiMsg.toolName = data.tool; list.value.push({ role: 'ai', content: '', type: 'tool', toolId: data.id, toolName: data.tool, toolInput: data.input }) }
        if (data.type === 'tool_result') { setTimeout(() => { if (list.value[aiIndex]) list.value[aiIndex].status = 'tool_done' }, Math.max(0, 800 - (Date.now() - toolCallingStart))); const t = [...list.value].reverse().find(m => m.type === 'tool' && m.toolId === data.id); if (t) t.toolOutput = data.output }
        if (data.type === 'done') {
            isStreaming = false
            if (isFirstMessage && chatStore.activeConversation?.title === '新对话') {
                generateTitle(chatStore.activeConversationId!, msg).then(res => {
                    chatStore.updateTitle(res.data.id, res.data.title)
                }).catch(() => {})
            }
            scrollToBottom()
        }
        if (data.type === 'error') {
            if (aiMsg) { aiMsg.status = 'error'; aiMsg.content = data.message || '请求失败，请重试' }
            isStreaming = false
        }
        scrollToBottom()
    },
    (error) => {
        const aiMsg = list.value[aiIndex]
        if (aiMsg) { aiMsg.status = 'error'; aiMsg.content = '网络错误，请检查连接后重试' }
        isStreaming = false
    },
    abortController.signal,
)
```

- [ ] **Step 2: 删除轮询逻辑**

删除第 177-200 行的 `if (isFirstMessage ...)` 和 `else` 两个分支（整个 `setInterval` + `setTimeout` 轮询逻辑）。这些已被 `done` 事件替代。

- [ ] **Step 3: 删除 `generateTitle` 从轮询移到 done 事件**

注意：`generateTitle` 调用已在 Step 1 的 `done` 分支中处理，不需要额外操作。

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/views/Chat/components/ChatArea.vue
git commit -m "fix(chat): handle done/error SSE events, remove polling"
```

---

### Task 5: ChatArea — 自动滚动 + 历史滚动（#1）

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 添加 `scrollToBottom` 函数**

在 `const chatRef = ...` 之后添加：

```typescript
function scrollToBottom() {
    const el = chatRef.value?.parentElement
    if (!el) return
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150
    if (isNearBottom) {
        nextTick(() => chatRef.value?.scrollIntoView({ behavior: 'smooth' }))
    }
}
```

- [ ] **Step 2: 删除旧的 watch**

删除第 206 行：
```typescript
watch(() => list.value.length, () => { nextTick(() => { chatRef.value?.scrollIntoView({ behavior: 'smooth' }) }) })
```

- [ ] **Step 3: 在 history 加载后调用 scrollToBottom**

在 `watch(() => chatStore.activeConversationId, ...)` 的 `list.value = res.data` 之后，加一行强制滚到底部（历史加载时用户一定想看最新消息，不受 isNearBottom 限制）：

```typescript
if (newId) {
    const res = await getChatHistory(newId)
    list.value = res.data
    nextTick(() => chatRef.value?.scrollIntoView({ behavior: 'smooth' }))  // 历史加载强制滚到底
}
```

- [ ] **Step 4: 验证 scrollToBottom 已在 SSE callback 中调用**

确认 Task 4 Step 1 中的 SSE callback 末尾已有 `scrollToBottom()` 调用。

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/views/Chat/components/ChatArea.vue
git commit -m "fix(chat): add smart auto-scroll with user position detection"
```

---

### Task 6: ChatArea — 错误 UI + 重试按钮（#2）

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 修改模板 — 错误状态 + 重试按钮**

在模板中 AI 消息的 status 判断区域，在 `tool_done` 之后添加 error 分支。将第 18-28 行改为：

```html
<div v-if="item.status === 'loading'" class="flex items-center gap-1 mt-2">
    <span class="loading-dot"></span><span class="loading-dot"></span><span class="loading-dot"></span>
</div>
<div v-else-if="item.status === 'tool_calling'" class="text-xs text-gray-400 mt-2">
    <span class="inline-block tool-shake">🔍</span>
    <span class="ml-1">正在调用 <strong>{{ item.toolName }}</strong>...</span>
</div>
<div v-else-if="item.status === 'tool_done'" class="text-xs text-green-500 mt-2">
    <span>✅</span><span class="ml-1"><strong>{{ item.toolName }}</strong> 查询完成</span>
</div>
<div v-else-if="item.status === 'error'" class="mt-2">
    <div class="text-xs text-red-500">{{ item.content }}</div>
    <el-button size="small" type="danger" plain class="!mt-1" @click="retryMessage(item)">重试</el-button>
</div>
```

- [ ] **Step 2: 发送时存 originalContent**

在 `sendMessage` 函数中，push AI 消息时加上 `originalContent`：

```typescript
list.value.push({ role: 'ai', content: '', reasoning: '', status: 'loading', type: 'chat', originalContent: msg })
```

- [ ] **Step 3: 添加 retryMessage 函数**

在 `handleSelectCard` 函数之后添加：

首先修改 ChatArea.vue 第 58 行的 import：
```typescript
// 原来：
import type { ChatMessageList, ChatDto, ChatSSEMessage } from '@en/common/chat'
// 改为：
import type { ChatMessageList, ChatDto, ChatSSEMessage, ChatMessage } from '@en/common/chat'
```

然后添加函数：
```typescript
function retryMessage(item: ChatMessage) {
    if (!item.originalContent) return
    message.value = item.originalContent
    // 移除错误的 AI 消息和对应的用户消息
    const idx = list.value.indexOf(item)
    if (idx > 0 && list.value[idx - 1]?.role === 'human') {
        list.value.splice(idx - 1, 2)
    } else {
        list.value.splice(idx, 1)
    }
    nextTick(() => sendMessage())
}
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/views/Chat/components/ChatArea.vue
git commit -m "feat(chat): add inline error display with retry button"
```

---

### Task 7: ChatArea — toolId 匹配修正（#11）

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

此改动已在 Task 4 Step 1 中完成 — `tool_result` 匹配已从 `m.toolName === data.tool` 改为 `m.toolId === data.id`。确认无遗漏即可。

- [ ] **Step 1: 验证匹配逻辑**

检查 SSE callback 中 `tool_result` 分支：
```typescript
const t = [...list.value].reverse().find(m => m.type === 'tool' && m.toolId === data.id)
```
确认用的是 `m.toolId === data.id`（不是 `m.toolName === data.tool`）。

- [ ] **Step 2: Commit（如需额外改动）**

如果 Task 4 已覆盖，无需额外 commit。

---

### 第一批验收

- [ ] **验收 1: 启动后端，确认无 import 错误**

```bash
cd server && uv run python -c "from ai.services.chat import stream_chat; print('ok')"
```

- [ ] **验收 2: 启动前端，确认无 TypeScript 错误**

```bash
cd apps/web && pnpm type-check
```

- [ ] **验收 3: 手动测试 — 发送消息，确认 done 事件正常结束流**

- [ ] **验收 4: 手动测试 — 断网后发送，确认行内错误显示 + 重试按钮可用**

---

## 第二批：UI/交互（#4, #5, #7, #9, #10）

### Task 8: 语法高亮 — highlight.js + marked-highlight（#4）

**Files:**
- Modify: `apps/web/package.json`
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 安装依赖**

```bash
cd apps/web && pnpm add highlight.js marked-highlight
```

- [ ] **Step 2: 配置 marked 使用 highlight.js**

在 `ChatArea.vue` 的 `<script setup>` 中，修改 import 和添加 marked 配置：

```typescript
import { marked } from 'marked'
import hljs from 'highlight.js'
import { markedHighlight } from 'marked-highlight'
import DOMPurify from 'dompurify'
import 'highlight.js/styles/github-dark.css'

marked.use(markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value
        }
        return hljs.highlightAuto(code).value
    }
}))
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/package.json apps/web/pnpm-lock.yaml apps/web/src/views/Chat/components/ChatArea.vue
git commit -m "feat(chat): add syntax highlighting with highlight.js"
```

---

### Task 9: 工具调用详情 — 折叠/展开（#5）

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 添加展开状态管理**

在 `const chatRef = ...` 附近添加：

```typescript
const expandedTools = ref<Set<string>>(new Set())
const toggleToolExpand = (toolId: string | undefined) => {
    if (!toolId) return
    if (expandedTools.value.has(toolId)) expandedTools.value.delete(toolId)
    else expandedTools.value.add(toolId)
}
```

- [ ] **Step 2: 修改模板 — tool 消息展示**

将第 13 行：
```html
<template v-else-if="item.type === 'tool'"></template>
```

改为：
```html
<div v-else-if="item.type === 'tool'" class="ml-12 my-1">
    <div @click="toggleToolExpand(item.toolId)" class="cursor-pointer text-xs text-gray-400 hover:text-gray-600 inline-flex items-center gap-1">
        <span>{{ item.toolName }}</span>
        <span v-if="item.toolOutput">✅</span>
        <span v-else>⏳</span>
        <span class="text-[10px]">{{ expandedTools.has(item.toolId ?? '') ? '▲' : '▼' }}</span>
    </div>
    <div v-if="expandedTools.has(item.toolId ?? '')" class="mt-1 text-xs text-gray-500 bg-gray-50 rounded p-2 max-w-[80%]">
        <div><strong>输入：</strong>{{ item.toolInput }}</div>
        <div v-if="item.toolOutput" class="mt-1"><strong>输出：</strong>{{ item.toolOutput }}</div>
    </div>
</div>
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/views/Chat/components/ChatArea.vue
git commit -m "feat(chat): add collapsible tool call details"
```

---

### Task 10: 对话删除确认（#7）

**Files:**
- Modify: `apps/web/src/views/Chat/components/ConversationList.vue`

- [ ] **Step 1: 添加 ElMessageBox 导入**

在 `<script setup>` 中添加：

```typescript
import { ElMessageBox } from 'element-plus'
```

- [ ] **Step 2: 修改 handleDelete 加确认弹窗**

将第 68-75 行改为：

```typescript
const handleDelete = async (id: string) => {
    try {
        await ElMessageBox.confirm('确定删除这个对话吗？', '提示', {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning',
        })
    } catch {
        return  // 用户取消
    }
    await chatStore.deleteConversation(id)
    if (chatStore.activeConversationId) {
        router.replace(`/chat/${chatStore.activeRole}/${chatStore.activeConversationId}`)
    } else {
        router.replace(`/chat/${chatStore.activeRole}`)
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/views/Chat/components/ConversationList.vue
git commit -m "fix(chat): add confirmation dialog before deleting conversation"
```

---

### Task 11: 输入长度限制（#9）

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 给 textarea 加 maxlength**

将第 46 行：
```html
<el-input @keyup.enter="sendMessage" type="textarea" :rows="2" v-model="message" :placeholder="inputPlaceholder" class="flex-1" />
```

改为：
```html
<el-input @keyup.enter="sendMessage" type="textarea" :rows="2" v-model="message" :placeholder="inputPlaceholder" maxlength="4000" show-word-limit class="flex-1" />
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/views/Chat/components/ChatArea.vue
git commit -m "fix(chat): add maxlength 4000 with word limit display"
```

---

### Task 12: 卡片填充输入框（#10）

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 修改 handleSelectCard**

将第 131-137 行改为：

```typescript
function handleSelectCard(placeholder: string, toggle?: 'deep' | 'web') {
    message.value = placeholder
    inputPlaceholder.value = '请输入内容'
    if (toggle === 'deep') { deepThink.value = true; webSearch.value = false }
    else if (toggle === 'web') { webSearch.value = true; deepThink.value = false }
    else { deepThink.value = false; webSearch.value = false }
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/views/Chat/components/ChatArea.vue
git commit -m "fix(chat): fill input on card click instead of just setting placeholder"
```

---

### 第二批验收

- [ ] **验收 1: TypeScript 检查**

```bash
cd apps/web && pnpm type-check
```

- [ ] **验收 2: 手动测试 — 发送含代码块的消息，确认语法高亮生效**

- [ ] **验收 3: 手动测试 — 触发工具调用，确认折叠/展开可用**

- [ ] **验收 4: 手动测试 — 删除对话，确认弹窗确认**

- [ ] **验收 5: 手动测试 — 输入超 4000 字，确认字数限制显示**

- [ ] **验收 6: 手动测试 — 点击欢迎页卡片，确认输入框被填充**

---

## 第三批：架构（#8）

### Task 13: 抽取 ensureValidToken + createAuthInterceptor（#8）

**Files:**
- Modify: `apps/web/src/apis/auth/index.ts`
- Modify: `apps/web/src/apis/index.ts`
- Modify: `apps/web/src/apis/sse/index.ts`
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 在 `apis/auth/index.ts` 中添加 `ensureValidToken`**

在文件末尾添加：

```typescript
import { useUserStore } from '@/stores/user'

/**
 * 统一 token 有效性检查，5s buffer。
 * 返回有效 token 字符串，或 null（需要重新登录）。
 */
export async function ensureValidToken(): Promise<string | null> {
    const userStore = useUserStore()
    const token = userStore.getAccessToken
    const refreshToken = userStore.getRefreshToken
    if (!token || !refreshToken) return null
    try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        if (Date.now() >= (payload.exp * 1000 - 5000)) {
            const result = await refreshTokenApi({ refreshToken })
            if (result.success) {
                userStore.updateToken(result.data)
                return result.data.accessToken
            }
            return null
        }
        return token
    } catch {
        return token
    }
}
```

- [ ] **Step 2: 在 `apis/auth/index.ts` 中添加 `createAuthInterceptor` 工厂函数**

```typescript
import type { AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

/**
 * 401 拦截器工厂函数。
 * 每个 Axios 实例独立的 isRefreshing 和 requestQueue，避免共享队列。
 */
export function createAuthInterceptor(getApi: () => AxiosInstance) {
    let isRefreshing = false
    let requestQueue: ((newAccessToken: string) => void)[] = []

    return async (error: any) => {
        if (error.code === 'ERR_NETWORK') {
            ElMessage.error('网络连接失败,请重试')
            return Promise.reject(error)
        }
        if (error.response?.status !== 401) {
            const msg = error.response?.data?.message || '服务器异常,请稍后再试'
            ElMessage.error(msg)
            return Promise.reject(error)
        }

        const userStore = useUserStore()
        const accessToken = userStore.getAccessToken
        const refreshToken = userStore.getRefreshToken
        const originalRequest = error.config

        if (!accessToken || !refreshToken) {
            userStore.logout()
            ElMessage.error('登录已过期,请重新登录')
            router.replace('/')
            return Promise.reject(error)
        }

        if (isRefreshing) {
            return new Promise((resolve) => {
                requestQueue.push((newAccessToken: string) => {
                    originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
                    resolve(getApi()(originalRequest))
                })
            })
        }

        isRefreshing = true
        try {
            const newToken = await refreshTokenApi({ refreshToken })
            if (newToken.success) {
                userStore.updateToken(newToken.data)
            } else {
                userStore.logout()
                ElMessage.error('登录已过期,请重新登录')
                router.replace('/')
                return Promise.reject(error)
            }
            const newAccessToken = newToken.data.accessToken
            requestQueue.forEach(callback => callback(newAccessToken))
            return getApi()(originalRequest)
        } catch (err) {
            return Promise.reject(err)
        } finally {
            requestQueue = []
            isRefreshing = false
        }
    }
}
```

- [ ] **Step 3: 修改 `apis/index.ts` — 使用工厂函数**

将 `apis/index.ts` 中第 14-79 行（serverApi 的 isRefreshing/requestQueue/拦截器）和第 81-144 行（aiApi 的同样逻辑）替换为：

```typescript
import axios from 'axios'
import { useUserStore } from '@/stores/user'
import { refreshTokenApi, createAuthInterceptor } from './auth'
import { ElMessage } from 'element-plus'

export const uploadUrl = import.meta.env.VITE_MINIO_ENDPOINT
export const socketUrl = import.meta.env.VITE_SOCKET_URL
export const timeout = 50000

// server 服务器接口
export const serverApi = axios.create({
    baseURL: '/api/v1',
    timeout,
})

// 请求拦截器
serverApi.interceptors.request.use(config => {
    const userStore = useUserStore()
    if (userStore.getAccessToken) {
        config.headers.Authorization = `Bearer ${userStore.getAccessToken}`
    }
    return config
})

// 响应拦截器 — 使用工厂函数
serverApi.interceptors.response.use(res => {
    return res.data
}, createAuthInterceptor(() => serverApi))

// ai 服务器接口
export const aiApi = axios.create({
    baseURL: '/ai/v1',
    timeout,
})

// 请求拦截器
aiApi.interceptors.request.use(config => {
    const userStore = useUserStore()
    if (userStore.getAccessToken) {
        config.headers.Authorization = `Bearer ${userStore.getAccessToken}`
    }
    return config
})

// 响应拦截器 — 使用工厂函数
aiApi.interceptors.response.use(res => {
    return res.data
}, createAuthInterceptor(() => aiApi))

export interface Response<T = any> {
    timestamp: string,
    path: string,
    message: string,
    code: number,
    success: boolean,
    data: T
}
```

- [ ] **Step 4: 修改 `sse/index.ts` — 使用 ensureValidToken**

将 `sse/index.ts` 中第 18-46 行的手动 token 检查替换为：

```typescript
import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { Method } from 'axios'
import { ensureValidToken } from '@/apis/auth'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

export const CHAT_URL = '/ai/v1/chat'

export const sse = async <T, V = any>(
    url: string,
    method: Method = "POST",
    body: V,
    callback?: (data: T) => void,
    errorCallback?: (error: Error) => void,
    signal?: AbortSignal,
) => {
    const token = await ensureValidToken()
    if (!token) {
        ElMessage.error('登录已过期，请重新登录')
        useUserStore().logout()
        router.replace('/')
        return
    }

    fetchEventSource(url, {
        method: method.toLowerCase(),
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
        openWhenHidden: false,
        signal,
        async onopen(response) {
            if (response.status === 401) {
                ElMessage.error('登录已过期，请重新登录')
                useUserStore().logout()
                router.replace('/')
                throw new Error('Unauthorized')
            }
            if (!response.ok) {
                const text = await response.text()
                throw new Error(text || `HTTP ${response.status}`)
            }
        },
        onmessage: (event) => {
            try {
                callback?.(JSON.parse(event.data) as T)
            } catch (e) {
                console.warn('SSE JSON parse error:', event.data, e)
            }
        },
        onerror(error) {
            errorCallback?.(error)
            throw error
        },
    })
}
```

- [ ] **Step 5: 修改 `ChatArea.vue` — 删除 ensureToken，使用 ensureValidToken**

删除第 74-90 行的 `ensureToken` 函数，将 `sendMessage` 中第 143 行的 `if (!await ensureToken()) return` 改为：

```typescript
import { ensureValidToken } from '@/apis/auth'

// sendMessage 中：
if (!await ensureValidToken()) return
```

同时删除顶部的 `import { refreshTokenApi } from '@/apis/auth'`（不再直接使用）。

- [ ] **Step 6: TypeScript 检查**

```bash
cd apps/web && pnpm type-check
```

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/apis/auth/index.ts apps/web/src/apis/index.ts apps/web/src/apis/sse/index.ts apps/web/src/views/Chat/components/ChatArea.vue
git commit -m "refactor(auth): unify token refresh into ensureValidToken + createAuthInterceptor"
```

---

### 第三批验收

- [ ] **验收 1: TypeScript 检查**

```bash
cd apps/web && pnpm type-check
```

- [ ] **验收 2: 手动测试 — 正常发消息，确认 token 刷新正常**

- [ ] **验收 3: 手动测试 — SSE 连接中 token 过期，确认自动刷新不中断**

- [ ] **验收 4: 手动测试 — 401 拦截器正常工作（两个 Axios 实例独立队列）**

---

## 最终验收

- [ ] **全量 TypeScript 检查**

```bash
pnpm type-check
```

- [ ] **全量构建**

```bash
pnpm build
```

- [ ] **完整手动回归测试**

1. 发送普通消息 → 确认自动滚动
2. 发送含代码块消息 → 确认语法高亮
3. 触发工具调用 → 确认折叠/展开
4. 断网发送 → 确认行内错误 + 重试
5. 删除对话 → 确认弹窗确认
6. 输入超 4000 字 → 确认字数限制
7. 点击欢迎卡片 → 确认输入框填充
8. 多次快速发消息 → 确认 token 刷新无竞态

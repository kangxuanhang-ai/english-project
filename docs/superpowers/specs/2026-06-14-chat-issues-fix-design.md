# Chat 模块 11 条问题修复设计

日期：2026-06-14

## 问题清单

| # | 问题 | 优先级 | 定性 |
|---|------|--------|------|
| 1 | 流式输出无自动滚动 | 🔴 P0 | Bug |
| 2 | SSE 流式错误静默吞掉 | 🔴 P0 | Bug |
| 3 | SSE onmessage 无容错 | 🔴 P0 | Bug |
| 4 | 代码块无语法高亮 | 🟡 P1 | 问题 |
| 5 | 工具调用详情不可见 | 🟡 P1 | 问题 |
| 6 | 流式完成检测靠轮询 | 🟡 P1 | 问题 |
| 7 | 对话删除无确认 | 🟡 P1 | 问题 |
| 8 | Token 刷新逻辑重复 3 处 | 🟡 P1 | 问题 |
| 9 | 输入无长度限制 | 🟡 P1 | 问题 |
| 10 | handleSelectCard 不填充输入框 | 🟡 P1 | UX 优化 |
| 11 | toolId 匹配逻辑缺陷（同名工具竞态） | 🟡 P1 | 架构缺陷 |

## 修复策略

按模块分三批：

1. **第一批：SSE/流式**（#1, #2, #3, #6, #11）— 稳定核心数据流
2. **第二批：UI/交互**（#4, #5, #7, #9, #10）— 改善用户体验
3. **第三批：架构**（#8）— 消除 Token 刷新重复

---

## 第一批：SSE/流式

### #6 流式完成检测 — 后端发 done 事件

**现状**：`ChatArea.vue:179-199` 用 `setInterval` 每秒轮询 + 10 秒硬超时检测流是否结束。不可靠 — AI 输出超过 10 秒时 `isStreaming` 会被提前设为 false。

**方案**：后端在流结束后 yield 一个 `data: {"type": "done"}` 事件。

**后端改动**（`server/ai/services/chat.py`）：
- 在 `for async for event in agent.astream_events(...)` 循环结束后，yield `data: {"type": "done"}`
- 流正常结束时发 done 事件
- 流异常结束时（如 checkpointer 连接断开、工具调用失败等），发 error 事件（`data: {"type": "error", "message": "..."}`），不发 done 事件
- 前端收到 error 事件时走错误处理流程，收到 done 事件时走正常结束流程

**前端改动**（`apps/web/src/views/Chat/components/ChatArea.vue`）：
- SSE callback 里增加 `type === 'done'` 分支：设 `isStreaming = false`
- SSE callback 里增加 `type === 'error'` 分支：设 AI 消息 `status = 'error'`，`isStreaming = false`
- 删除所有 `setInterval` + `setTimeout` 轮询逻辑
- done 事件同时触发一次滚动到底部

### #2 SSE 错误处理 — 行内错误

**现状**：`ChatArea.vue:173` 给 `sse()` 传 `undefined` 作为 errorCallback。网络错误、服务端 500 等无任何反馈，AI 消息停留在 loading 状态。

**方案**：错误时在 AI 消息气泡内显示行内错误提示。

**前端改动**（`ChatArea.vue`）：
- 给 `sse()` 传 error callback：把 AI 消息的 `status` 改为 `'error'`，设 `isStreaming = false`
- 发送时在 AI 消息上存 `originalContent: msg`（原始用户消息），供重试使用（需在 `ChatMessage` 类型中添加 `originalContent?: string`）
- 模板增加 `v-else-if="item.status === 'error'"` 分支，显示红色"请求失败，请重试"文案 + 重试按钮
- 重试按钮点击时：从 AI 消息的 `originalContent` 恢复消息，调用 `sendMessage()` 重新发送

**前端改动**（`sse/index.ts`）：
- 当前代码已按正确顺序调用（先 errorCallback 再 throw），问题在于 ChatArea.vue 传了 undefined。修复方式是传入有效的 error callback

### #3 JSON 容错 — try-catch

**现状**：`sse/index.ts:70` 的 `JSON.parse(event.data)` 没有 try-catch。后端发非 JSON 数据时整个流崩溃。

**方案**：加 try-catch，catch 里只 warn 日志，跳过这条消息，让流继续。不调 errorCallback — 单条 JSON 解析失败不应触发错误 UI。

**前端改动**（`sse/index.ts`）：
```typescript
onmessage: (event) => {
    try {
        callback?.(JSON.parse(event.data) as T)
    } catch (e) {
        console.warn('SSE JSON parse error:', event.data, e)
        // 跳过这条，让流继续
    }
}
```

### #1 自动滚动 — 在 SSE callback 里触发

**现状**：`watch(() => list.value.length, ...)` 只监听数组长度。流式输出往同一条消息追加内容，长度不变，watch 不触发。

**方案**：删除 watch，在 SSE callback 里每次 append content 后触发滚动。加用户位置判断 — 如果用户往上滚在看历史消息，不强制拉到底部。

**前端改动**（`ChatArea.vue`）：
- 删除 `watch(() => list.value.length, ...)`
- 抽取 `scrollToBottom()` 函数：
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
- 在 SSE callback 的 `reasoning`、`chat`、`tool`、`tool_result`、`done` 分支末尾调 `scrollToBottom()`
- 在 `watch(() => chatStore.activeConversationId, ...)` 的 history 加载完成后也调 `scrollToBottom()`（否则删除 watch 后加载历史不会自动滚到底部）

### #11 toolId 匹配 — 用 LangGraph 事件自带 ID

**现状**：`chat.py:113` 生成随机 `call_id = str(uuid.uuid4())[:8]`，前端存了 `toolId` 但匹配时用 `toolName`。同名工具多次调用时会匹配错误。

**方案**：用 LangGraph `astream_events` v2 的 `run_id` 做关联。同一个 tool call 的 `on_tool_start` 和 `on_tool_end` 共享同一个 `run_id`（`event.get("id")` 是每个事件自己的唯一 ID，不能做关联）。

**后端改动**（`chat.py`）：
```python
# on_tool_start
call_id = str(event.get("run_id", ""))
yield f"data: {json.dumps({'type': 'tool', 'id': call_id, ...})}\n\n"

# on_tool_end
call_id = str(event.get("run_id", ""))
yield f"data: {json.dumps({'type': 'tool_result', 'id': call_id, ...})}\n\n"
```

**前端改动**（`ChatArea.vue`）：
- `tool_result` 匹配改为 `reverse().find(m => m.type === 'tool' && m.toolId === data.id)`

---

## 第二批：UI/交互

### #4 代码块语法高亮 — highlight.js

**现状**：`deep-seek.css` 定义了 `.keyword`/`.function`/`.string` 等 class，但没有加载语法高亮库。这些 CSS class 是死代码。

**方案**：引入 highlight.js + `marked-highlight` 包。项目用 `marked: ^17.0.1`，`setOptions({ highlight })` 在 v5+ 已废弃，需用 `marked.use()` + 扩展。

**改动**：
- 安装 `highlight.js` 和 `marked-highlight` 依赖
- 在 markdown 解析处配置 marked：
  ```typescript
  import hljs from 'highlight.js'
  import { markedHighlight } from 'marked-highlight'
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
- 在入口文件或 ChatArea.vue 引入 highlight.js 的 CSS 主题

### #5 工具调用详情 — 折叠/展开

**现状**：`<template v-else-if="item.type === 'tool'"></template>` 渲染空。用户只看到"正在调用...🔍"，不知道具体输入输出。

**方案**：默认折叠，显示工具名 + 状态；点击展开看输入输出详情。

**前端改动**（`ChatArea.vue`）：
- 用独立的 `Set<string>` 管理展开状态（不往 `ChatMessage` 共享类型加 `expanded` 字段）：
  ```typescript
  const expandedTools = ref<Set<string>>(new Set())
  const toggleToolExpand = (toolId: string) => {
      if (expandedTools.value.has(toolId)) expandedTools.value.delete(toolId)
      else expandedTools.value.add(toolId)
  }
  ```
- 为 tool 类型消息增加折叠/展开 UI：
  ```html
  <div v-else-if="item.type === 'tool'" class="tool-detail">
      <div @click="toggleToolExpand(item.toolId)" class="cursor-pointer text-xs text-gray-400">
          <span>{{ item.toolName }}</span>
          <span v-if="item.toolOutput"> ✅ 完成</span>
          <span v-else> ⏳ 运行中</span>
      </div>
      <div v-if="expandedTools.has(item.toolId)" class="mt-1 text-xs text-gray-500 bg-gray-50 rounded p-2">
          <div><strong>输入：</strong>{{ item.toolInput }}</div>
          <div v-if="item.toolOutput"><strong>输出：</strong>{{ item.toolOutput }}</div>
      </div>
  </div>
  ```

### #7 对话删除确认

**现状**：`ConversationList.vue:68-75` 点击删除直接执行，无确认。

**方案**：用 `ElMessageBox.confirm` 包一层。

**前端改动**（`ConversationList.vue`）：
```typescript
const handleDelete = async (id: string) => {
    try {
        await ElMessageBox.confirm('确定删除这个对话吗？', '提示', {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning',
        })
        await chatStore.deleteConversation(id)
        // ...路由跳转逻辑
    } catch {}
}
```

### #9 输入长度限制

**现状**：`ChatArea.vue:46` 的 `<el-input type="textarea">` 没有 `maxlength`。后端限制 4000 字符但前端无提示。

**方案**：加 `maxlength="4000"` + `show-word-limit`。

**前端改动**（`ChatArea.vue`）：
```html
<el-input @keyup.enter="sendMessage" type="textarea" :rows="2" v-model="message"
    :placeholder="inputPlaceholder" maxlength="4000" show-word-limit class="flex-1" />
```

### #10 卡片填充输入框

**现状**：`handleSelectCard` 把卡片文本赋给 `inputPlaceholder`，`message.value` 被清空。用户点击卡片后还得手动打字。

**方案**：把卡片文本赋给 `message.value`，同时重置 `inputPlaceholder` 为通用文案。

**前端改动**（`ChatArea.vue`）：
```typescript
function handleSelectCard(placeholder: string, toggle?: 'deep' | 'web') {
    message.value = placeholder  // 填充输入框，用户可直接发送或编辑
    inputPlaceholder.value = '请输入内容'  // 重置 placeholder，避免重复
    if (toggle === 'deep') { deepThink.value = true; webSearch.value = false }
    else if (toggle === 'web') { webSearch.value = true; deepThink.value = false }
    else { deepThink.value = false; webSearch.value = false }
}
```

---

## 第三批：架构

### #8 Token 刷新去重

**现状**：三处各自实现 token 刷新逻辑：
1. `apis/index.ts` — serverApi 和 aiApi 的 401 响应拦截器（代码几乎一样）
2. `sse/index.ts` — SSE 连接前检查
3. `ChatArea.vue` — `ensureToken()` 发消息前检查

buffer 时间不一致（5s vs 10s）。`requestQueue` 是模块级变量，serverApi 和 aiApi 共享同一个队列。

**方案**：提取到 `apis/auth.ts`，导出两个函数。

**`apis/auth.ts` 新增**：
```typescript
// 统一 token 有效性检查，5s buffer
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

// 401 拦截器工厂函数，每个 Axios 实例独立队列
export function createAuthInterceptor(getApi: () => AxiosInstance) {
    let isRefreshing = false
    let requestQueue: ((token: string) => void)[] = []

    return async (error: any) => {
        // ...401 处理逻辑，使用局部的 isRefreshing 和 requestQueue
    }
}
```

**`apis/index.ts` 改动**：
```typescript
import { createAuthInterceptor } from './auth'
serverApi.interceptors.response.use(res => res.data, createAuthInterceptor(() => serverApi))
aiApi.interceptors.response.use(res => res.data, createAuthInterceptor(() => aiApi))
```

**`sse/index.ts` 改动**：
- 用 `ensureValidToken()` 替换手动的 token 检查和刷新逻辑

**`ChatArea.vue` 改动**：
- 删除 `ensureToken()` 函数
- 用 `ensureValidToken()` 替换

---

## 涉及文件

| 文件 | 改动批次 | 改动内容 |
|------|----------|---------|
| `server/ai/services/chat.py` | 第一批 | done 事件 + toolId 改用 LangGraph run_id |
| `apps/web/src/apis/sse/index.ts` | 第一批 + 第三批 | JSON 容错（跳过不中断）+ ensureValidToken |
| `apps/web/src/views/Chat/components/ChatArea.vue` | 第一批 + 第二批 | 自动滚动 + 历史滚动 + 错误展示 + 重试按钮 + 工具详情 + 输入限制 + 卡片填充 |
| `apps/web/src/views/Chat/components/ConversationList.vue` | 第二批 | 删除确认 |
| `apps/web/src/assets/css/deep-seek.css` | 第二批 | 可能需要调整高亮样式 |
| `apps/web/src/apis/auth.ts` | 第三批 | ensureValidToken + createAuthInterceptor |
| `apps/web/src/apis/index.ts` | 第三批 | 用工厂函数替换重复拦截器 |
| `apps/web/package.json` | 第二批 | 添加 highlight.js + marked-highlight 依赖 |
| `packages/common/chat/index.ts` | 第一批 | ChatMessage 添加 originalContent 字段（供重试用） |

# Chat 三栏布局改造设计

## 概述

将 Chat 页面从现有的两栏布局（角色列表 + 聊天区）改造为三栏布局（角色列表 + 历史对话列表 + 聊天区），支持每个角色拥有多个独立对话。

## 背景

### 现状

- 两栏布局：`Conversations.vue`（角色列表）+ `Bubble.vue`（聊天区）
- 每个角色只有一条对话，thread_id = `{userId}-{role}`
- 对话历史完全由 LangGraph `AsyncPostgresSaver` 管理，无自定义表
- 前端无 Pinia chat store，状态在 `Chat/index.vue` 组件本地

### 目标

- 三栏布局：角色列表 + 历史对话列表 + 聊天区
- 每个角色可创建多个独立对话
- 对话标题由 AI 自动生成
- 支持删除对话
- 数据持久化在后端（PostgreSQL + LangGraph checkpointer）

## §1 后端数据模型

### 新建 conversations 表

```python
# server/app/models/conversation.py
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str]          # UUID, 主键, 同时作为 LangGraph thread_id
    user_id: Mapped[str]     # String(30), FK -> user.id (nanoid)
    role: Mapped[str]        # 'normal' | 'master' | 'business' | 'qilinge' | 'xiaoman'
    title: Mapped[str]       # AI 生成的标题，默认 "新对话"
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # 关系
    user = relationship("User", back_populates="conversations")
```

### 关键设计决策

1. **thread_id = conversation.id**：直接用 UUID 作为 LangGraph thread_id，不拼接 userId 和 role。对话归属关系由 conversations 表维护。

2. **消息继续存在 LangGraph 中**：不建 messages 表，Conversation 只存元数据。

3. **数据库**：conversations 表建在 `english` 数据库（和 User 等表一起），不在 `langchain` 数据库。

4. **级联删除**：删除 Conversation 时，同时调用 `checkpointer.adelete_thread(id)` 清除 LangGraph 消息。

5. **user_id 类型**：`Mapped[str] = mapped_column(String(30))`，与 User 主键一致（nanoid）。

### 数据迁移

丢弃旧对话数据。现有 thread_id 格式（`{userId}-{role}`）的对话不迁移，从零开始。

### Alembic 迁移

生成新迁移文件，创建 conversations 表。

### `app/models/__init__.py` 更新

新增 `Conversation` 的导入和 `__all__` 导出，否则 Alembic 无法检测到新表。

### `app/models/user.py` 更新

User 模型新增 conversations 关系，确保删用户时级联删除所有对话：

```python
conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
```

Conversation 模型对应添加 `user = relationship("User", back_populates="conversations")`。

### `updated_at` 触发机制

LangGraph checkpointer 不会更新 conversations 表。需要在 `POST /ai/v1/chat` 接口的 `stream_chat` 调用之前，手动更新：

```python
conversation.updated_at = func.now()
await db.commit()
```

这样活跃对话在中栏列表中始终排在最前面（按 `updated_at DESC` 排序）。

## §2 后端接口设计

### 新增接口

#### POST `/ai/v1/chat/conversations` — 新建对话

```
Request:  { "role": "normal" }
Response: { "id": "uuid", "role": "normal", "title": "新对话", "createdAt": "...", "updatedAt": "..." }
```

#### GET `/ai/v1/chat/conversations?role=xxx` — 获取对话列表

```
Response: [
  { "id": "uuid-1", "role": "normal", "title": "帮我查abandon用法", "createdAt": "...", "updatedAt": "..." },
  { "id": "uuid-2", "role": "normal", "title": "翻译商务邮件", "createdAt": "...", "updatedAt": "..." }
]
```

按 `updated_at` 降序排列。

#### DELETE `/ai/v1/chat/conversations/{id}` — 删除对话

- 删除 conversations 记录
- 调用 `checkpointer.adelete_thread(id)` 清除 LangGraph 消息
- 校验 user_id 匹配，防止删别人的对话

#### POST `/ai/v1/chat/conversations/title` — 生成对话标题

```
Request:  { "conversationId": "uuid", "firstMessage": "帮我查一下abandon的用法" }
Response: { "id": "uuid", "title": "查询abandon单词用法" }
```

- 用 `deepseek-chat` 轻量模型，prompt 限制 15 字以内
- 降级逻辑：AI 调用失败时，截取 firstMessage 前 15 个字作为标题
- 无论成功失败都更新 conversations.title 并返回

### 修改接口

#### POST `/ai/v1/chat` — 发送消息

ChatDto 新增必填字段 `conversationId`：

```json
{
  "conversationId": "uuid",
  "role": "normal",
  "content": "帮我查一下abandon",
  "deepThink": false,
  "webSearch": false
}
```

`stream_chat` 内部 thread_id 改为直接用 `conversationId`。

#### GET `/ai/v1/chat/history` — 获取历史

参数从 `?role=xxx` 改为 `?conversationId=xxx`。

#### DELETE `/ai/v1/chat/history` — 移除

此接口不再需要。删除对话由 `DELETE /ai/v1/chat/conversations/{id}` 处理（级联删除记录 + LangGraph 消息）。原接口从 router 中删除。

### 标题生成流程

1. 用户发送第一条消息
2. SSE 流正常返回
3. 流结束后，前端检查 `activeConversation.title === "新对话"`
4. 如果是，调用 `POST /ai/v1/chat/conversations/title`
5. 拿到标题后调用 `chatStore.updateTitle(id, title)` 更新中栏

前端驱动，后端不负责通知。

## §3 前端组件拆分

### 组件树

```
views/Chat/index.vue                    # 三栏布局容器
├── components/RoleList.vue             # 左栏：角色列表
├── components/ConversationList.vue     # 中栏：对话列表
└── components/ChatArea.vue             # 右栏：聊天区
```

### 组件职责

#### RoleList.vue（左栏，~200px）

- 调 `getChatMode()` 获取角色列表
- 渲染角色卡片，当前角色高亮
- 点击 → `chatStore.setRole(role)`
- 不持有本地状态，纯消费 store

#### ConversationList.vue（中栏，~280px）

- 顶部 "+ 新对话" 按钮
- 列表：显示当前角色的所有对话，当前对话高亮
- 每条对话：标题 + 删除按钮（hover 显示）
- 点击对话 → `chatStore.setConversation(id)`
- 新建对话 → `chatStore.createConversation(role)`
- 删除对话 → `chatStore.deleteConversation(id)`

#### ChatArea.vue（右栏，flex-1）

- 复用现有 Bubble.vue 的消息渲染逻辑（Markdown、工具调用状态、推理展示）
- 输入框、Deep Think / Web Search 开关、语音输入
- 消息列表 `list` 作为本地状态，切换对话时从 `/history` 接口拉取
- 发送消息时从 store 取 `activeConversationId` 和 `role`
- SSE 流结束后，检查标题是否为 "新对话"，是则调 `/title` 更新
- **SSE 中断机制**：用 `AbortController` 管理当前 SSE 连接。切换对话或角色时，调用 `abort()` 中断旧流，防止消息串到新对话。`onUnmounted` 时也 abort。

### 与现有结构的对应关系

| 现有 | 改造后 | 变化 |
|------|--------|------|
| `Conversations.vue` | `RoleList.vue` | 重命名，功能不变 |
| — | `ConversationList.vue` | 全新组件 |
| `Bubble.vue` | `ChatArea.vue` | 重构，状态从 props 改为 store |

`Chat/index.vue` 从「持有 list 状态 + 角色切换逻辑」变为纯布局容器。

## §4 状态管理

### 新建 `stores/chat.ts`

```ts
export const useChatStore = defineStore('chat', () => {
  const activeRole = ref<ChatRoleType>('normal')
  const activeConversationId = ref<string | null>(null)
  const conversations = ref<Conversation[]>([])

  const activeConversation = computed(() =>
    conversations.value.find(c => c.id === activeConversationId.value)
  )

  async function setRole(role: ChatRoleType) { ... }
  function setConversation(id: string) { ... }
  async function createConversation(role: ChatRoleType): Promise<string> { ... }
  async function deleteConversation(id: string) { ... }
  function updateTitle(id: string, title: string) { ... }

  return { activeRole, activeConversationId, conversations,
           activeConversation, setRole, setConversation,
           createConversation, deleteConversation, updateTitle }
})
```

### 关键行为

1. **setRole**：切换角色 → 拉取该角色对话列表 → 默认选中第一条。无对话时 `activeConversationId = null`，右栏显示空状态。

2. **deleteConversation**：删除后自动选中列表中下一条。列表为空时 `activeConversationId = null`。

3. **初始化**：Chat/index.vue 的 `onMounted` 调用 `chatStore.setRole('normal')`。

4. **不持久化**：每次进入页面从后端拉最新数据。

### 分工原则

- **Store**：对话元数据（角色、对话列表、当前对话 ID）
- **ChatArea**：消息内容（本地 ref，切换对话时重新拉取）
- 两者不交叉

## §5 路由设计

### 路由配置

```ts
// router/chat/index.ts
export default [{
  path: '/chat',
  component: layout,
  children: [
    { path: ':role/:conversationId?', component: () => import('@/views/Chat/index.vue') }
  ]
}]
```

`conversationId` 为可选参数。

### URL 格式

```
/chat/:role/:conversationId
/chat/normal/550e8400-e29b-41d4-a716-446655440000
```

### 路由守卫逻辑（Chat/index.vue 中处理）

1. **正常进入**：URL 带 role + conversationId → store 设为对应状态，拉取对话列表和消息
2. **只带 role**：`/chat/normal` → 拉取对话列表，自动选中第一条。无对话则显示空状态
3. **无参数**：`/chat` → 重定向到 `/chat/normal`
4. **无效 conversationId**：对话不存在 → 重定向到该角色的对话列表

### 路由与 store 同步

**路由是唯一源头，组件负责路由跳转**。避免 store ↔ 路由双向更新导致死循环：

- **页面进入/刷新**：路由参数 → `Chat/index.vue` 的 `onMounted` 调用 `chatStore.setRole(role)` → 拉列表 → 选中对话。这是初始化路径。
- **用户操作（点击角色/对话）**：由组件（RoleList、ConversationList）调用 `router.replace()` 更新 URL，同时调用 store 方法更新数据。store 只管数据，不管路由。
- **store watcher 不监听路由变化**：只在初始化时从路由读一次，之后路由和 store 各管各的。

### Header 导航链接

将 `/chat/index` 改为 `/chat`。

## 前端 API 层变更

### `apis/chat/index.ts` 新增

```ts
// 新建对话
export const createConversation = (role: ChatRoleType) =>
    aiApi.post('/chat/conversations', { role }) as Promise<Response<Conversation>>

// 获取对话列表
export const getConversations = (role: ChatRoleType) =>
    aiApi.get(`/chat/conversations?role=${role}`) as Promise<Response<Conversation[]>>

// 删除对话
export const deleteConversation = (id: string) =>
    aiApi.delete(`/chat/conversations/${id}`) as Promise<Response<void>>

// 生成标题
export const generateTitle = (conversationId: string, firstMessage: string) =>
    aiApi.post('/chat/conversations/title', { conversationId, firstMessage }) as Promise<Response<{ id: string; title: string }>>
```

### `apis/chat/index.ts` 修改

```ts
// 修改：参数从 role 改为 conversationId
export const getChatHistory = (conversationId: string) =>
    aiApi.get(`/chat/history?conversationId=${conversationId}`) as Promise<Response<ChatMessageList>>

// 删除：原 deleteChatHistory 接口移除，改用 deleteConversation
```

### `packages/common/chat/index.ts` 新增类型

```ts
export type Conversation = {
  id: string
  role: ChatRoleType
  title: string
  createdAt: string
  updatedAt: string
}
```

### `ChatDto` 修改

```ts
export type ChatDto = {
  conversationId: string  // 新增必填
  deepThink: boolean
  webSearch: boolean
  role: ChatRoleType
  content: string
}
```

### `apis/sse/index.ts` 修改

`sse()` 函数新增可选参数 `signal?: AbortSignal`，透传给 `fetchEventSource` 的 `fetch` 选项，使调用方可以通过 `AbortController` 中断 SSE 连接。

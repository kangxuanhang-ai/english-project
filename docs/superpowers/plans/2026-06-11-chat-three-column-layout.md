# Chat 三栏布局改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Chat 页面从两栏改造为三栏布局，支持每个角色多个独立对话。

**Architecture:** 新增 `conversations` 表存储对话元数据（标题、角色、归属），消息继续存在 LangGraph checkpointer 中。thread_id 从 `{userId}-{role}` 改为 `{conversationId}`（UUID）。前端新增 Pinia chat store 管理对话元数据，ChatArea 本地管理消息列表。

**Tech Stack:** Vue 3 + TypeScript + Pinia + Tailwind CSS 4（前端），FastAPI + SQLAlchemy + LangGraph + DeepSeek（后端）

---

## 文件变更总览

### 后端（server/）

| 操作 | 文件 | 职责 |
|------|------|------|
| Create | `app/models/conversation.py` | Conversation ORM 模型 |
| Modify | `app/models/__init__.py` | 导入 Conversation |
| Modify | `app/models/user.py` | 新增 conversations 关系 |
| Create | `alembic/versions/xxx_add_conversations.py` | Alembic 迁移 |
| Create | `ai/routers/conversation.py` | 对话 CRUD 路由 |
| Create | `ai/schemas/conversation.py` | 对话 Pydantic schemas |
| Modify | `ai/routers/chat.py` | 修改 history 参数、移除 delete_history |
| Modify | `ai/schemas/chat.py` | ChatRequest 新增 conversationId |
| Modify | `ai/services/chat.py` | thread_id 改用 conversationId、updated_at 触发 |
| Modify | `ai/main.py` | 注册 conversation router |

### 前端（apps/web/）

| 操作 | 文件 | 职责 |
|------|------|------|
| Modify | `packages/common/chat/index.ts` | 新增 Conversation 类型、修改 ChatDto |
| Modify | `src/apis/chat/index.ts` | 新增对话 API、修改 getChatHistory |
| Modify | `src/apis/sse/index.ts` | sse() 新增 AbortSignal 参数 |
| Create | `src/stores/chat.ts` | Pinia chat store |
| Modify | `src/router/chat/index.ts` | 路由改为 /chat/:role/:conversationId? |
| Create | `src/views/Chat/components/RoleList.vue` | 左栏角色列表 |
| Create | `src/views/Chat/components/ConversationList.vue` | 中栏对话列表 |
| Create | `src/views/Chat/components/ChatArea.vue` | 右栏聊天区（重构自 Bubble.vue） |
| Modify | `src/views/Chat/index.vue` | 三栏布局容器 |
| Modify | `src/layout/Header/index.vue` | 导航链接 /chat/index → /chat |
| Delete | `src/views/Chat/components/Conversations.vue` | 旧角色列表（被 RoleList 替代） |
| Delete | `src/views/Chat/components/Bubble.vue` | 旧聊天区（被 ChatArea 替代） |

---

## Task 1: 后端 — Conversation 模型 + User 关系

**Files:**
- Create: `server/app/models/conversation.py`
- Modify: `server/app/models/__init__.py`
- Modify: `server/app/models/user.py`

### Step 1: 创建 Conversation 模型

创建 `server/app/models/conversation.py`：

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(30), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(100), default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="conversations")

    # 索引：常用查询 WHERE user_id = ? AND role = ?
    __table_args__ = (
        Index("idx_conversation_user_role", "user_id", "role"),
    )
```

### Step 2: 更新 `app/models/__init__.py`

在 `server/app/models/__init__.py` 中添加 Conversation 的导入和导出：

```python
from app.models.user import User
from app.models.word_book import WordBook, WordBookRecord
from app.models.course import Course, CourseRecord
from app.models.payment import PaymentRecord, TradeStatus
from app.models.visitor import (
    Visitor,
    PageView,
    TrackEvent,
    PerformanceEntry,
    ErrorEntry,
)
from app.models.conversation import Conversation  # 新增

__all__ = [
    "User",
    "WordBook",
    "WordBookRecord",
    "Course",
    "CourseRecord",
    "PaymentRecord",
    "TradeStatus",
    "Visitor",
    "PageView",
    "TrackEvent",
    "PerformanceEntry",
    "ErrorEntry",
    "Conversation",  # 新增
]
```

### Step 3: 更新 `app/models/user.py`

在 `server/app/models/user.py` 的关系区块末尾添加：

```python
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
```

### Step 4: 验证模型可导入

```bash
cd server && uv run python -c "from app.models import Conversation; print('OK')"
```

Expected: `OK`

---

## Task 2: 后端 — Alembic 迁移

**Files:**
- Create: `server/alembic/versions/xxx_add_conversations_table.py`

### Step 1: 生成迁移文件

```bash
cd server && uv run alembic revision --autogenerate -m "add conversations table"
```

### Step 2: 检查生成的迁移文件

打开新生成的迁移文件，确认 `upgrade()` 中包含 `op.create_table('conversations', ...)` 以及正确的列定义（id, user_id, role, title, created_at, updated_at）和外键约束。

### Step 3: 执行迁移

```bash
cd server && uv run alembic upgrade head
```

Expected: `Running upgrade ... -> xxx, add conversations table`

### Step 4: 验证表已创建

```bash
cd server && uv run python -c "
import asyncio
from app.database import engine
async def check():
    async with engine.connect() as conn:
        result = await conn.execute(__import__('sqlalchemy').text(\"SELECT column_name FROM information_schema.columns WHERE table_name='conversations'\"))
        for row in result: print(row[0])
asyncio.run(check())
```

Expected: 输出 id, user_id, role, title, created_at, updated_at

---

## Task 3: 后端 — Conversation CRUD 路由 + Schemas

**Files:**
- Create: `server/ai/schemas/conversation.py`
- Create: `server/ai/routers/conversation.py`
- Modify: `server/ai/main.py`

### Step 1: 创建 Conversation Schemas

创建 `server/ai/schemas/conversation.py`：

```python
from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=20)


class GenerateTitleRequest(BaseModel):
    conversationId: str = Field(..., min_length=1)
    firstMessage: str = Field(..., min_length=1, max_length=500)
```

### Step 2: 创建 Conversation 路由

创建 `server/ai/routers/conversation.py`：

```python
import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.database import get_db
from app.models.conversation import Conversation
from ai.schemas.conversation import CreateConversationRequest, GenerateTitleRequest
from ai.services.chat import get_checkpointer

router = APIRouter(prefix="/ai/v1/chat/conversations", tags=["conversations"])


@router.post("")
async def create_conversation(
    data: CreateConversationRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新建对话。"""
    conversation = Conversation(
        user_id=user["userId"],
        role=data.role,
        title="新对话",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return {
        "data": {
            "id": conversation.id,
            "role": conversation.role,
            "title": conversation.title,
            "createdAt": conversation.created_at.isoformat() if conversation.created_at else None,
            "updatedAt": conversation.updated_at.isoformat() if conversation.updated_at else None,
        },
        "code": 200,
        "message": "创建成功",
    }


@router.get("")
async def list_conversations(
    role: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取某角色的对话列表，按 updated_at 降序。"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user["userId"], Conversation.role == role)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()
    return {
        "data": [
            {
                "id": c.id,
                "role": c.role,
                "title": c.title,
                "createdAt": c.created_at.isoformat() if c.created_at else None,
                "updatedAt": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in conversations
        ],
        "code": 200,
        "message": "查询成功",
    }


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除对话（级联清除 LangGraph 消息）。"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user["userId"],
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 先删 LangGraph 消息
    try:
        checkpointer = await get_checkpointer()
        await checkpointer.adelete_thread(conversation_id)
    except Exception:
        traceback.print_exc()  # LangGraph 删除失败不阻塞记录删除

    # 再删数据库记录
    await db.delete(conversation)
    await db.commit()
    return {"data": None, "code": 200, "message": "删除成功"}
```

### Step 3: 在 `ai/main.py` 注册路由

在 `server/ai/main.py` 中，导入并注册 conversation router：

```python
# 在已有的 import 行后添加
from ai.routers import prompt, chat, conversation

# 在 include_router 区域添加
ai_app.include_router(conversation.router)
```

### Step 4: 在 conversation router 中添加标题生成路由

在 `server/ai/routers/conversation.py` 末尾添加：

```python
@router.post("/title")
async def generate_conversation_title(
    data: GenerateTitleRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成对话标题。"""
    from ai.services.chat import generate_title

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == data.conversationId,
            Conversation.user_id == user["userId"],
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    title = await generate_title(data.firstMessage)
    conversation.title = title
    await db.commit()
    await db.refresh(conversation)
    return {
        "data": {"id": conversation.id, "title": conversation.title},
        "code": 200,
        "message": "生成成功",
    }
```

### Step 5: 验证路由注册

```bash
cd server && uv run python -c "from ai.routers.conversation import router; print('Routes:', [r.path for r in router.routes])"
```

Expected: 输出包含 ``, `/{conversation_id}`, `/title` 等路径

---

## Task 4: 后端 — 修改 Chat 服务和路由

**Files:**
- Modify: `server/ai/schemas/chat.py`
- Modify: `server/ai/services/chat.py`
- Modify: `server/ai/routers/chat.py`

### Step 1: 修改 ChatRequest Schema

在 `server/ai/schemas/chat.py` 中新增 `conversationId` 字段：

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    role: str = "normal"
    deepThink: bool = False
    webSearch: bool = False
    conversationId: str = Field(..., min_length=1)  # 新增必填
```

### Step 2: 修改 `stream_chat` — thread_id 改用 conversationId

在 `server/ai/services/chat.py` 中：

1. 在 `data.get` 区域新增 `conversation_id` 提取：

```python
    role = data.get("role", "normal")
    content = data.get("content", "")
    deep_think = data.get("deepThink", False)
    web_search = data.get("webSearch", False)
    user_id = data.get("userId", "")
    conversation_id = data.get("conversationId", "")  # 新增
```

2. 将 `thread_id = f"{user_id}-{role}"` 改为：

```python
    thread_id = conversation_id
```

3. 在 retry 循环中，`checkpointer.adelete_thread(thread_id)` 不变（已经是用 thread_id）。

### Step 3: 修改 `get_chat_history` — 参数改为 conversationId

将 `server/ai/services/chat.py` 中的 `get_chat_history` 函数签名和实现改为：

```python
async def get_chat_history(conversation_id: str) -> list:
    """获取对话历史。"""
    for attempt in range(2):
        checkpointer = await get_checkpointer()
        thread_id = conversation_id
        try:
            state = await checkpointer.aget({"configurable": {"thread_id": thread_id}})
            if not state or not state.get("channel_values", {}).get("messages"):
                return []

            messages = state["channel_values"]["messages"]
            result = []
            for msg in messages:
                item = {
                    "content": msg.content,
                    "role": msg.type,
                    "reasoning": getattr(msg, "additional_kwargs", {}).get(
                        "reasoning_content"
                    ),
                }
                if msg.type == "tool":
                    item["toolName"] = getattr(msg, "name", None) or getattr(msg, "tool_call_id", None)
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    item["toolCalls"] = [
                        {"name": tc.get("name", ""), "args": tc.get("args", {})}
                        for tc in msg.tool_calls
                    ]
                result.append(item)
            return result
        except OperationalError as e:
            print(f"Database connection error: {e}")
            if attempt == 0:
                await reset_checkpointer()
            else:
                return []
        except Exception as e:
            print(f"Error getting chat history: {e}")
            traceback.print_exc()
            return []
```

### Step 4: 新增标题生成函数

在 `server/ai/services/chat.py` 末尾添加：

```python
async def generate_title(first_message: str) -> str:
    """用 AI 生成对话标题（15字以内），失败时降级为截取消息前15字。"""
    try:
        model = create_deepseek()
        from langchain_core.messages import HumanMessage
        response = await model.ainvoke([
            HumanMessage(content=f"用不超过15个字概括这段对话的主题，只返回标题文字，不要标点：{first_message}")
        ])
        title = response.content.strip().strip('"').strip("'").strip("。").strip(".")
        if len(title) > 15:
            title = title[:15]
        return title if title else first_message[:15]
    except Exception:
        # 降级：截取前15个字
        return first_message[:15]
```

### Step 5: 修改 Chat 路由

将 `server/ai/routers/chat.py` 改为：

```python
import json
import traceback

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.database import get_db
from app.models.conversation import Conversation
from ai.schemas.chat import ChatRequest
from ai.services.chat import stream_chat, get_chat_history

router = APIRouter(prefix="/ai/v1/chat", tags=["chat"])


@router.post("")
async def chat(
    data: ChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE 流式聊天。"""
    # 更新对话的 updated_at，让活跃对话排到最前面
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == data.conversationId,
            Conversation.user_id == user["userId"],
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation:
        from sqlalchemy import func
        conversation.updated_at = func.now()
        await db.commit()

    chat_data = data.model_dump()
    chat_data["userId"] = user["userId"]

    async def _stream():
        try:
            async for chunk in stream_chat(chat_data):
                yield chunk
        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'content': '[错误] 对话出错，请重试', 'role': 'ai', 'type': 'chat'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/history")
async def history(conversationId: str, user: dict = Depends(get_current_user)):
    """对话历史。"""
    result = await get_chat_history(conversationId)
    return {"data": result, "code": 200, "message": "查询成功"}
```

注意：**`DELETE /history` 接口已移除**，删除对话由 `DELETE /ai/v1/chat/conversations/{id}` 处理。**`POST /title` 已移至 conversation router**。

### Step 6: 验证后端启动

```bash
cd server && uv run python -c "from ai.main import ai_app; print('Routes:', [r.path for r in ai_app.routes])"
```

Expected: 输出包含 `/ai/v1/chat`, `/ai/v1/chat/history`, `/ai/v1/chat/conversations` 等路径（/title 在 conversation router 下）

---

## Task 5: 前端 — 共享类型 + API 层

**Files:**
- Modify: `packages/common/chat/index.ts`
- Modify: `apps/web/src/apis/chat/index.ts`
- Modify: `apps/web/src/apis/sse/index.ts`

### Step 1: 更新共享类型

将 `packages/common/chat/index.ts` 改为：

```ts
export type ChatRole = 'human' | 'ai';
export type ChatRoleType = 'normal' | 'master' | 'business' | 'qilinge' | 'xiaoman';
export type ChatMessageType = 'reasoning' | 'chat' | 'tool' | 'tool_result';
export type ChatStatus = 'loading' | 'tool_calling' | 'tool_done';
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
}
export type ChatMessageList = ChatMessage[]

/** SSE 服务端推送的 wire format（短字段名） */
export type ChatSSEMessage = {
    type: ChatMessageType
    content?: string
    role?: ChatRole
    reasoning?: string
    id?: string
    tool?: string
    input?: string
    output?: string
}

export type ChatMode = {
    label: string;
    id: string;
    role: ChatRoleType;
}
export type ChatModeList = ChatMode[]

export type ChatDto = {
    conversationId: string  // 新增必填
    deepThink: boolean;
    webSearch: boolean;
    role: ChatRoleType;
    content: string;
}

/** 对话元数据 */
export type Conversation = {
    id: string
    role: ChatRoleType
    title: string
    createdAt: string
    updatedAt: string
}
```

### Step 2: 更新 Chat API

将 `apps/web/src/apis/chat/index.ts` 改为：

```ts
import { aiApi, type Response } from '..'
import type { ChatModeList, ChatRoleType, ChatMessageList, Conversation } from '@en/common/chat'

// 获取消息模式列表
export const getChatMode = () =>
    aiApi.get('/prompt/list') as Promise<Response<ChatModeList>>

// 获取历史记录（参数改为 conversationId）
export const getChatHistory = (conversationId: string) =>
    aiApi.get(`/chat/history?conversationId=${conversationId}`) as Promise<Response<ChatMessageList>>

// 新建对话
export const createConversation = (role: ChatRoleType) =>
    aiApi.post('/chat/conversations', { role }) as Promise<Response<Conversation>>

// 获取对话列表
export const getConversations = (role: ChatRoleType) =>
    aiApi.get(`/chat/conversations?role=${role}`) as Promise<Response<Conversation[]>>

// 删除对话
export const deleteConversationApi = (id: string) =>
    aiApi.delete(`/chat/conversations/${id}`) as Promise<Response<void>>

// 生成标题（路由在 conversation router 下）
export const generateTitle = (conversationId: string, firstMessage: string) =>
    aiApi.post('/chat/conversations/title', { conversationId, firstMessage }) as Promise<Response<{ id: string; title: string }>>
```

### Step 3: 更新 SSE 层 — 新增 AbortSignal 支持

将 `apps/web/src/apis/sse/index.ts` 的 `sse` 函数改为（完整代码）：

```ts
import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { Method } from 'axios'
import { useUserStore } from '@/stores/user'
import { refreshTokenApi } from '@/apis/auth'
import { ElMessage } from 'element-plus'
import router from '@/router'

export const CHAT_URL = '/ai/v1/chat'

function isTokenExpired(token: string): boolean {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        return Date.now() >= (payload.exp * 1000 - 2000)
    } catch {
        return true
    }
}

export const sse = async <T, V = any>(
    url: string,
    method: Method = "POST",
    body: V,
    callback?: (data: T) => void,
    errorCallback?: (error: Error) => void,
    signal?: AbortSignal,  // 新增可选参数
    onComplete?: () => void,  // 新增：SSE 流正常结束时回调
) => {
    const userStore = useUserStore()
    let token = userStore.getAccessToken
    const refreshToken = userStore.getRefreshToken

    if (!token || !refreshToken) {
        ElMessage.error('登录已过期，请重新登录')
        userStore.logout()
        router.replace('/')
        return
    }

    if (isTokenExpired(token)) {
        try {
            const result = await refreshTokenApi({ refreshToken })
            if (result.success) {
                userStore.updateToken(result.data)
                token = result.data.accessToken
            } else {
                ElMessage.error('登录已过期，请重新登录')
                userStore.logout()
                router.replace('/')
                return
            }
        } catch {
            // 刷新失败，用当前 token 尝试
        }
    }

    fetchEventSource(url, {
        method: method.toLowerCase(),
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
        openWhenHidden: false,
        signal,  // 新增：透传 AbortSignal
        async onopen(response) {
            if (response.status === 401) {
                ElMessage.error('登录已过期，请重新登录')
                userStore.logout()
                router.replace('/')
                throw new Error('Unauthorized')
            }
            if (!response.ok) {
                const text = await response.text()
                throw new Error(text || `HTTP ${response.status}`)
            }
        },
        onmessage: (event) => {
            callback?.(JSON.parse(event.data) as T)
        },
        onerror(error) {
            // 不 throw = 停止重连（fetchEventSource 的规则）
            // AbortError：用户主动中断
            // 其他情况：SSE 流正常结束或出错，统一停止并回调
            errorCallback?.(error)
            onComplete?.()
            // 不 throw，让连接自然关闭
        },
    })
}
```

### Step 4: 验证类型检查

```bash
cd apps/web && pnpm type-check
```

Expected: 无类型错误（可能有其他文件的现有错误，忽略即可）

---

## Task 6: 前端 — Pinia Chat Store

**Files:**
- Create: `apps/web/src/stores/chat.ts`

### Step 1: 创建 Chat Store

创建 `apps/web/src/stores/chat.ts`：

```ts
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { ChatRoleType, Conversation } from '@en/common/chat'
import {
    getConversations,
    createConversation as createConversationApi,
    deleteConversationApi,
} from '@/apis/chat'

export const useChatStore = defineStore('chat', () => {
    const activeRole = ref<ChatRoleType>('normal')
    const activeConversationId = ref<string | null>(null)
    const conversations = ref<Conversation[]>([])

    const activeConversation = computed(() =>
        conversations.value.find(c => c.id === activeConversationId.value)
    )

    /** 切换角色：拉取对话列表，默认选中第一条 */
    async function setRole(role: ChatRoleType) {
        activeRole.value = role
        activeConversationId.value = null
        try {
            const res = await getConversations(role)
            conversations.value = res.data
            if (res.data.length > 0) {
                activeConversationId.value = res.data[0].id
            }
        } catch {
            conversations.value = []
        }
    }

    /** 切换对话 */
    function setConversation(id: string) {
        activeConversationId.value = id
    }

    /** 新建对话：创建并设为 active */
    async function createConversation(role: ChatRoleType): Promise<string> {
        const res = await createConversationApi(role)
        const conv = res.data
        conversations.value.unshift(conv)
        activeConversationId.value = conv.id
        return conv.id
    }

    /** 删除对话：自动切到下一条 */
    async function deleteConversation(id: string) {
        await deleteConversationApi(id)
        const idx = conversations.value.findIndex(c => c.id === id)
        conversations.value = conversations.value.filter(c => c.id !== id)

        // 如果删的是当前对话，切到最近一条
        if (activeConversationId.value === id) {
            if (conversations.value.length > 0) {
                // 切到同位置或前一条
                const newIdx = Math.min(idx, conversations.value.length - 1)
                activeConversationId.value = conversations.value[newIdx].id
            } else {
                activeConversationId.value = null
            }
        }
    }

    /** 更新对话标题 */
    function updateTitle(id: string, title: string) {
        const conv = conversations.value.find(c => c.id === id)
        if (conv) {
            conv.title = title
        }
    }

    return {
        activeRole,
        activeConversationId,
        conversations,
        activeConversation,
        setRole,
        setConversation,
        createConversation,
        deleteConversation,
        updateTitle,
    }
})
```

### Step 2: 验证 store 可导入

```bash
cd apps/web && pnpm type-check
```

Expected: 无新增类型错误

---

## Task 7: 前端 — 路由配置

**Files:**
- Modify: `apps/web/src/router/chat/index.ts`

### Step 1: 更新路由配置

将 `apps/web/src/router/chat/index.ts` 改为：

```ts
import layout from '@/layout/index.vue'

export default [
    {
        path: '/chat',
        component: layout,
        children: [
            { path: ':role/:conversationId?', component: () => import('@/views/Chat/index.vue') },
        ]
    }
]
```

`conversationId` 为可选参数（`?`）。

### Step 2: 验证路由注册

```bash
cd apps/web && pnpm type-check
```

Expected: 无新增类型错误

---

## Task 8: 前端 — RoleList 组件（左栏）

**Files:**
- Create: `apps/web/src/views/Chat/components/RoleList.vue`

### Step 1: 创建 RoleList 组件

创建 `apps/web/src/views/Chat/components/RoleList.vue`：

```vue
<template>
    <div class="w-[200px] bg-purple-50 border-r border-gray-200 flex flex-col">
        <div class="p-4 border-b border-gray-200">
            <h3 class="text-sm font-bold text-gray-600">角色</h3>
        </div>
        <div class="flex-1 overflow-y-auto p-2">
            <div
                v-for="mode in chatModes"
                :key="mode.id"
                @click="handleClick(mode)"
                :class="{
                    'bg-purple-300': chatStore.activeRole === mode.role,
                    'hover:bg-purple-100': chatStore.activeRole !== mode.role,
                }"
                class="rounded-[5px] p-2 px-4 cursor-pointer transition-all duration-200 mb-1"
            >
                <div class="text-sm text-gray-700">{{ mode.label }}</div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { ChatModeList, ChatMode } from '@en/common/chat'
import { getChatMode } from '@/apis/chat'
import { useChatStore } from '@/stores/chat'
import { useRouter } from 'vue-router'

const chatStore = useChatStore()
const router = useRouter()
const chatModes = ref<ChatModeList>([])

const handleClick = (mode: ChatMode) => {
    chatStore.setRole(mode.role)
    router.replace(`/chat/${mode.role}`)
}

onMounted(async () => {
    const res = await getChatMode()
    chatModes.value = res.data
})
</script>
```

### Step 2: 验证组件可渲染

```bash
cd apps/web && pnpm type-check
```

Expected: 无新增类型错误

---

## Task 9: 前端 — ConversationList 组件（中栏）

**Files:**
- Create: `apps/web/src/views/Chat/components/ConversationList.vue`

### Step 1: 创建 ConversationList 组件

创建 `apps/web/src/views/Chat/components/ConversationList.vue`：

```vue
<template>
    <div class="w-[280px] bg-gray-50 border-r border-gray-200 flex flex-col">
        <!-- 顶部：新建对话按钮 -->
        <div class="p-4 border-b border-gray-200">
            <el-button
                type="primary"
                class="w-full"
                @click="handleCreate"
            >
                + 新对话
            </el-button>
        </div>

        <!-- 对话列表 -->
        <div class="flex-1 overflow-y-auto p-2">
            <div
                v-for="conv in chatStore.conversations"
                :key="conv.id"
                @click="handleSelect(conv.id)"
                :class="{
                    'bg-blue-100 border-blue-300': chatStore.activeConversationId === conv.id,
                    'hover:bg-gray-100 border-transparent': chatStore.activeConversationId !== conv.id,
                }"
                class="group rounded-[5px] p-3 px-4 cursor-pointer transition-all duration-200 mb-1 border flex items-center justify-between"
            >
                <div class="text-sm text-gray-700 truncate flex-1 mr-2">
                    {{ conv.title }}
                </div>
                <el-button
                    type="danger"
                    size="small"
                    link
                    class="opacity-0 group-hover:opacity-100 transition-opacity"
                    @click.stop="handleDelete(conv.id)"
                >
                    <el-icon><Delete /></el-icon>
                </el-button>
            </div>

            <!-- 空状态 -->
            <div
                v-if="chatStore.conversations.length === 0"
                class="text-center text-gray-400 text-sm mt-10"
            >
                暂无对话，点击上方新建
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { Delete } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import { useRouter } from 'vue-router'

const chatStore = useChatStore()
const router = useRouter()

const handleCreate = async () => {
    const id = await chatStore.createConversation(chatStore.activeRole)
    router.replace(`/chat/${chatStore.activeRole}/${id}`)
}

const handleSelect = (id: string) => {
    chatStore.setConversation(id)
    router.replace(`/chat/${chatStore.activeRole}/${id}`)
}

const handleDelete = async (id: string) => {
    await chatStore.deleteConversation(id)
    // 删除后自动切到新对话（store 已处理）
    if (chatStore.activeConversationId) {
        router.replace(`/chat/${chatStore.activeRole}/${chatStore.activeConversationId}`)
    } else {
        router.replace(`/chat/${chatStore.activeRole}`)
    }
}
</script>
```

### Step 2: 验证组件可渲染

```bash
cd apps/web && pnpm type-check
```

Expected: 无新增类型错误

---

## Task 10: 前端 — ChatArea 组件（右栏，重构自 Bubble.vue）

**Files:**
- Create: `apps/web/src/views/Chat/components/ChatArea.vue`

### Step 1: 创建 ChatArea 组件

创建 `apps/web/src/views/Chat/components/ChatArea.vue`。此组件重构自 `Bubble.vue`，核心变化：
- 消息列表从 props 改为本地 ref
- 从 store 读取 activeConversationId 和 activeRole
- SSE 发送时传入 conversationId
- 新增 AbortController 管理 SSE 连接
- 切换对话时重新拉取历史
- SSE 流结束后检查标题是否需要生成

```vue
<template>
    <div v-if="!chatStore.activeConversationId" class="flex-1 flex items-center justify-center bg-purple-50">
        <div class="text-center text-gray-400">
            <div class="text-4xl mb-4">💬</div>
            <div class="text-sm">选择一个对话或新建对话开始聊天</div>
        </div>
    </div>
    <div v-else class="flex-1 h-[750px] p-5 bg-purple-50 flex flex-col">
        <div class="flex-1 overflow-y-auto">
            <div v-for="(item, index) in list" :key="index">
                <div class="flex justify-end items-center gap-4 mt-5 mb-5 mr-5" v-if="item.role === 'human'">
                    <div class="text-sm text-white max-w-[80%] rounded-lg p-2 bg-blue-500 shadow-md">{{ item.content }}</div>
                    <div><el-avatar :size="35">user</el-avatar></div>
                </div>
                <template v-else-if="item.type === 'tool'"></template>
                <div v-else class="flex justify-start items-center gap-4 mt-5 mb-5">
                    <div><el-avatar :size="35">AI</el-avatar></div>
                    <div>
                        <div v-if="item.reasoning" class="text-[12px] text-gray-500 max-w-[80%] p-2">{{ item.reasoning }}</div>
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
                        <div v-if="item.content !== ''" class="text-sm text-gray-700 max-w-[80%] bg-white rounded-lg mt-2 deepseek-markdown" v-html="parseMarkdown(item.content)" />
                    </div>
                </div>
            </div>
            <div ref="chatRef"></div>
        </div>
        <div class="flex p-5 border-t border-gray-200 box-border flex-col gap-3">
            <div class="flex items-center gap-3">
                <div class="flex items-center gap-1 px-3 py-1 rounded-full text-xs cursor-pointer transition-all border"
                    :class="deepThink ? 'bg-purple-100 border-purple-400 text-purple-700' : 'bg-gray-100 border-gray-200 text-gray-500 hover:bg-gray-200'"
                    @click="toggleDeepThink"><span>🧠</span><span>深度思考</span></div>
                <div class="flex items-center gap-1 px-3 py-1 rounded-full text-xs cursor-pointer transition-all border"
                    :class="webSearch ? 'bg-blue-100 border-blue-400 text-blue-700' : 'bg-gray-100 border-gray-200 text-gray-500 hover:bg-gray-200'"
                    @click="toggleWebSearch"><span>🌐</span><span>联网搜索</span></div>
            </div>
            <div class="flex">
                <el-input @keyup.enter="sendMessage" type="textarea" :rows="2" v-model="message" placeholder="请输入内容" />
                <el-button class="ml-2" :icon="Position" type="primary" @click="sendMessage"></el-button>
                <el-button v-if="!isRecording" class="ml-2" :icon="Mic" type="primary" @click="startRecording"></el-button>
                <el-button v-else class="ml-2" :icon="VideoPause" type="primary" @click="stopRecording"></el-button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, useTemplateRef, watch, nextTick, onUnmounted } from 'vue'
import { Position, Mic, VideoPause } from '@element-plus/icons-vue'
import type { ChatMessageList, ChatDto, ChatSSEMessage } from '@en/common/chat'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import '@/assets/css/deep-seek.css'
import { useVoiceToText } from '@/hooks/useVoiceToText'
import { useChatStore } from '@/stores/chat'
import { getChatHistory, generateTitle } from '@/apis/chat'
import { sse, CHAT_URL } from '@/apis/sse'

const chatStore = useChatStore()
const { isRecording, start, stop } = useVoiceToText({ lang: 'zh-CN', continuous: true })

const list = ref<ChatMessageList>([])
const message = ref('')
const deepThink = ref(false)
const webSearch = ref(false)
const chatRef = useTemplateRef<HTMLDivElement>('chatRef')

let abortController: AbortController | null = null
let toolCallingStart = 0

watch(() => chatStore.activeConversationId, async (newId) => {
    if (abortController) { abortController.abort(); abortController = null }
    if (newId) {
        const res = await getChatHistory(newId)
        list.value = res.data
    } else {
        list.value = []
    }
})

const toggleDeepThink = () => { deepThink.value = !deepThink.value; if (deepThink.value) webSearch.value = false }
const toggleWebSearch = () => { webSearch.value = !webSearch.value; if (webSearch.value) deepThink.value = false }

const sendMessage = () => {
    if (!message.value || !chatStore.activeConversationId) return
    const msg = message.value; message.value = ''
    list.value.push({ role: 'human', content: msg, type: 'chat' })
    list.value.push({ role: 'ai', content: '', reasoning: '', status: 'loading', type: 'chat' })
    const aiIndex = list.value.length - 1
    const isFirstMessage = list.value.filter(m => m.role === 'human').length === 1

    if (abortController) abortController.abort()
    abortController = new AbortController()

    sse<ChatSSEMessage, ChatDto>(CHAT_URL, "POST",
        { conversationId: chatStore.activeConversationId!, role: chatStore.activeRole, content: msg, deepThink: deepThink.value, webSearch: webSearch.value },
        (data) => {
            if (data.type === 'reasoning') { list.value[aiIndex].reasoning += data.content ?? ''; if (list.value[aiIndex].status === 'loading') list.value[aiIndex].status = undefined }
            if (data.type === 'chat') { if (list.value[aiIndex].status) list.value[aiIndex].status = undefined; list.value[aiIndex].content += data.content ?? '' }
            if (data.type === 'tool') { toolCallingStart = Date.now(); list.value[aiIndex].status = 'tool_calling'; list.value[aiIndex].toolName = data.tool; list.value.push({ role: 'ai', content: '', type: 'tool', toolId: data.id, toolName: data.tool, toolInput: data.input }) }
            if (data.type === 'tool_result') { setTimeout(() => { list.value[aiIndex].status = 'tool_done' }, Math.max(0, 800 - (Date.now() - toolCallingStart))); const t = [...list.value].reverse().find(m => m.type === 'tool' && m.toolName === data.tool); if (t) t.toolOutput = data.output }
        },
        undefined,
        abortController.signal,
        // onComplete: SSE 流结束后生成标题
        async () => {
            if (isFirstMessage && chatStore.activeConversation?.title === '新对话' && chatStore.activeConversationId) {
                try { const res = await generateTitle(chatStore.activeConversationId, msg); chatStore.updateTitle(res.data.id, res.data.title) } catch {}
            }
        }
    )
}

const parseMarkdown = (content: string) => content ? DOMPurify.sanitize(marked.parse(content) as string) : ''
const startRecording = () => start((result) => { message.value = result })
const stopRecording = () => { stop(); sendMessage() }
watch(() => list.value.length, () => { nextTick(() => { chatRef.value?.scrollIntoView({ behavior: 'smooth' }) }) })
onUnmounted(() => { if (abortController) abortController.abort() })
</script>

<style scoped>
.loading-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background-color: #9ca3af; animation: dot-bounce 1.4s infinite ease-in-out both; }
.loading-dot:nth-child(1) { animation-delay: -0.32s; } .loading-dot:nth-child(2) { animation-delay: -0.16s; } .loading-dot:nth-child(3) { animation-delay: 0s; }
@keyframes dot-bounce { 0%, 80%, 100% { transform: scale(0); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }
.tool-shake { animation: shake 0.6s infinite; }
@keyframes shake { 0%, 100% { transform: translateX(0); } 20% { transform: translateX(-2px) rotate(-5deg); } 40% { transform: translateX(2px) rotate(5deg); } 60% { transform: translateX(-2px) rotate(-3deg); } 80% { transform: translateX(2px) rotate(3deg); } }
</style>
```

### Step 2: 验证组件可渲染

```bash
cd apps/web && pnpm type-check
```

Expected: 无新增类型错误

---

## Task 11: 前端 — Chat/index.vue 三栏布局 + Header 修复 + 清理

**Files:**
- Modify: `apps/web/src/views/Chat/index.vue`
- Modify: `apps/web/src/layout/Header/index.vue`
- Delete: `apps/web/src/views/Chat/components/Conversations.vue`
- Delete: `apps/web/src/views/Chat/components/Bubble.vue`

### Step 1: 重写 Chat/index.vue

将 `apps/web/src/views/Chat/index.vue` 改为：

```vue
<template>
    <div class="w-[1200px] mx-auto flex mt-10">
        <RoleList />
        <ConversationList />
        <ChatArea />
    </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import RoleList from './components/RoleList.vue'
import ConversationList from './components/ConversationList.vue'
import ChatArea from './components/ChatArea.vue'
import type { ChatRoleType } from '@en/common/chat'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()

const VALID_ROLES: ChatRoleType[] = ['normal', 'master', 'business', 'qilinge', 'xiaoman']

onMounted(async () => {
    const role = route.params.role as string
    const conversationId = route.params.conversationId as string | undefined
    if (!role || !VALID_ROLES.includes(role as ChatRoleType)) { router.replace('/chat/normal'); return }
    await chatStore.setRole(role as ChatRoleType)
    if (conversationId) {
        if (chatStore.conversations.some(c => c.id === conversationId)) {
            chatStore.setConversation(conversationId)
        } else {
            router.replace(`/chat/${role}`)
        }
    }
})
</script>
```

### Step 2: 修复 Header 导航链接

将 `apps/web/src/layout/Header/index.vue` 中的：

```ts
{ path: '/chat/index', name: '聊天', icon: MagicStick, isAuth: true },
```

改为：

```ts
{ path: '/chat', name: '聊天', icon: MagicStick, isAuth: true },
```

同时修复 `isActive` 逻辑：

```ts
const isActive = (path: string) => {
    if (path === '/chat') {
        return currentPath.value.startsWith('/chat') ? 'bg-blue-200 text-blue-700' : 'text-gray-500 hover:bg-blue-200 hover:text-blue-700'
    }
    return currentPath.value === path ? 'bg-blue-200 text-blue-700' : 'text-gray-500 hover:bg-blue-200 hover:text-blue-700'
}
```

### Step 3: 删除旧组件

```bash
rm apps/web/src/views/Chat/components/Conversations.vue
rm apps/web/src/views/Chat/components/Bubble.vue
```

### Step 4: 验证前端编译

```bash
cd apps/web && pnpm type-check && pnpm build
```

Expected: 编译成功，无错误

### Step 5: 启动全栈验证

```bash
# 终端 1
cd server && uv run python -m uvicorn ai.main:ai_app --port 3001 --reload

# 终端 2
pnpm web
```

Expected: 浏览器访问 `http://localhost:8080/chat`，看到三栏布局。可新建对话、切换角色、发送消息。

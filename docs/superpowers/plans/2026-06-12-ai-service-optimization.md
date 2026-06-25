# AI Service Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 16 security, performance, and code quality issues in the AI service (`server/ai/`).

**Architecture:** Incremental fixes across 10 files. Each task is self-contained and can be verified independently. Changes follow the existing codebase patterns (FastAPI + SQLAlchemy async + LangGraph).

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy (asyncpg), LangGraph, httpx, slowapi

---

### Task 1: Code Cleanup (#14, #15, #16)

**Files:**
- Modify: `server/ai/main.py:2` — delete unused `import selectors`
- Modify: `server/ai/services/chat.py:199` — delete duplicate import
- Modify: `server/ai/services/tools/progress.py:29` — SQLAlchemy style fix

- [ ] **Step 1: Delete unused import in main.py**

In `server/ai/main.py`, delete line 2 (`import selectors`):

```python
# Before:
import asyncio
import selectors
import sys

# After:
import asyncio
import sys
```

- [ ] **Step 2: Delete duplicate import in chat.py**

In `server/ai/services/chat.py`, delete the duplicate import inside `generate_title` (line 199). The top of the file already has `from langchain_core.messages import HumanMessage, SystemMessage`.

```python
# Before (inside generate_title):
    model = create_deepseek()
    from langchain_core.messages import HumanMessage
    response = await model.ainvoke([

# After:
    model = create_deepseek()
    response = await model.ainvoke([
```

- [ ] **Step 3: Fix SQLAlchemy boolean comparison in progress.py**

In `server/ai/services/tools/progress.py`, change `== True` to `.is_(True)`:

```python
# Before (line 29):
.where(WordBookRecord.is_master == True)

# After:
.where(WordBookRecord.is_master.is_(True))
```

- [ ] **Step 4: Verify changes**

```bash
cd server && uv run python -c "from ai.main import ai_app; print('main.py OK')"
cd server && uv run python -c "from ai.services.chat import stream_chat; print('chat.py OK')"
cd server && uv run python -c "from ai.services.tools.progress import make_progress_query; print('progress.py OK')"
```

- [ ] **Step 5: Commit**

```bash
git add server/ai/main.py server/ai/services/chat.py server/ai/services/tools/progress.py
git commit -m "fix: clean up unused/duplicate imports and SQLAlchemy style (#14, #15, #16)"
```

---

### Task 2: Conversation Ownership Validation (#4)

**Files:**
- Modify: `server/ai/routers/chat.py` — add 404 on missing/unauthorized conversation in both `chat` and `history` endpoints

- [ ] **Step 1: Fix chat endpoint ownership check**

In `server/ai/routers/chat.py`, after the conversation query (line 32), add a 404 check. Currently the code only skips the `updated_at` update when conversation is None — it should raise 404 instead:

```python
# Before (lines 32-36):
    conversation = result.scalar_one_or_none()
    if conversation:
        from sqlalchemy import func
        conversation.updated_at = func.now()
        await db.commit()

# After:
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    from sqlalchemy import func
    conversation.updated_at = func.now()
    await db.commit()
```

Note: `HTTPException` is already imported at line 3 (`from fastapi import APIRouter, Depends, HTTPException`).

- [ ] **Step 2: Fix history endpoint ownership check**

In `server/ai/routers/chat.py`, the `history` endpoint (line 56) has no ownership check at all. Add it:

```python
# Before (lines 56-60):
@router.get("/history")
async def history(conversationId: str, user: dict = Depends(get_current_user)):
    """对话历史。"""
    result = await get_chat_history(conversationId)
    return {"data": result, "code": 200, "message": "查询成功"}

# After:
@router.get("/history")
async def history(
    conversationId: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对话历史。"""
    # 归属校验
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversationId,
            Conversation.user_id == user["userId"],
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = await get_chat_history(conversationId)
    return {"data": messages, "code": 200, "message": "查询成功"}
```

This requires adding `AsyncSession` and `select` imports — but they're already imported at the top of the file (lines 6-7). The `get_db` dependency is also already imported (line 8).

- [ ] **Step 3: Verify**

```bash
cd server && uv run python -c "from ai.routers.chat import router; print('chat router OK')"
```

- [ ] **Step 4: Commit**

```bash
git add server/ai/routers/chat.py
git commit -m "fix: add conversation ownership validation on chat and history endpoints (#4)"
```

---

### Task 3: Schema Validation + Conversation List Limit (#12, #13)

**Files:**
- Modify: `server/ai/schemas/conversation.py` — add Literal type constraint
- Modify: `server/ai/routers/conversation.py:51` — add `.limit(200)`

- [ ] **Step 1: Add Literal role constraint**

In `server/ai/schemas/conversation.py`, change the `role` field to use `Literal`:

```python
# Before:
from pydantic import BaseModel, Field

class CreateConversationRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=20)

# After:
from typing import Literal
from pydantic import BaseModel, Field

class CreateConversationRequest(BaseModel):
    role: Literal['normal', 'master', 'business', 'qilinge', 'xiaoman']
```

This removes the `min_length`/`max_length` constraints (no longer needed — Literal restricts to exact values) and rejects any invalid role at the schema level.

- [ ] **Step 2: Add conversation list limit**

In `server/ai/routers/conversation.py`, add `.limit(200)` to the list query:

```python
# Before (lines 51-56):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user["userId"], Conversation.role == role)
        .order_by(Conversation.updated_at.desc())
    )

# After:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user["userId"], Conversation.role == role)
        .order_by(Conversation.updated_at.desc())
        .limit(200)
    )
```

- [ ] **Step 3: Verify**

```bash
cd server && uv run python -c "from ai.schemas.conversation import CreateConversationRequest; print('schema OK')"
cd server && uv run python -c "from ai.routers.conversation import router; print('conversation router OK')"
```

- [ ] **Step 4: Commit**

```bash
git add server/ai/schemas/conversation.py server/ai/routers/conversation.py
git commit -m "fix: add role validation and conversation list limit (#12, #13)"
```

---

### Task 4: Prompt Injection Fix (#5)

**Files:**
- Modify: `server/ai/services/chat.py:62-100` — restructure message flow

- [ ] **Step 1: Refactor stream_chat message construction**

In `server/ai/services/chat.py`, restructure the prompt and message handling. The key change: user `content` goes into `HumanMessage` (not system prompt), search results stay in system prompt.

Replace the current block (lines 62-100) in `stream_chat`:

```python
# Before:
    prompt = prompt_obj["prompt"]

    # 兜底：deepThink 和 webSearch 互斥，优先 deepThink
    if deep_think and web_search:
        web_search = False

    # 联网搜索增强
    if web_search:
        search_results = await create_bocha_search(content)
        if search_results:
            prompt += f"""
请根据以下搜索结果回答问题（并且返回你参考的网站名称），用户问题：{content}

{search_results}
"""
        # search_results 为空时降级为普通对话，不修改 prompt

    # 选择模型
    model = create_deepseek_reasoner() if deep_think else create_deepseek()

    # 创建 agent（连接断开 / 历史脏数据时自动重试一次）
    for attempt in range(2):
        checkpointer = await get_checkpointer()
        # normal 角色使用工具，其他角色保持空工具
        tools = make_tools(user_id) if role == "normal" else []
        agent = create_react_agent(
            model=model,
            tools=tools,
            checkpointer=checkpointer,
            prompt=SystemMessage(content=prompt),  # 注入 system prompt
        )

        thread_id = conversation_id
        try:
            messages = [HumanMessage(content=content)]

# After:
    prompt = prompt_obj["prompt"]

    # 兜底：deepThink 和 webSearch 互斥，优先 deepThink
    if deep_think and web_search:
        web_search = False

    # 联网搜索增强：搜索结果放 system prompt，用户问题始终作为 HumanMessage
    if web_search:
        search_results = await create_bocha_search(content)
        if search_results:
            prompt += f"""
请根据以下搜索结果回答问题（并且返回你参考的网站名称）：

{search_results}
"""
        # search_results 为空时降级为普通对话，不修改 prompt

    # 选择模型
    model = create_deepseek_reasoner() if deep_think else create_deepseek()

    # 创建 agent（连接断开 / 历史脏数据时自动重试一次）
    for attempt in range(2):
        checkpointer = await get_checkpointer()
        # normal 角色使用工具，其他角色保持空工具
        tools = make_tools(user_id) if role == "normal" else []
        agent = create_react_agent(
            model=model,
            tools=tools,
            checkpointer=checkpointer,
            prompt=SystemMessage(content=prompt),  # 注入 system prompt
        )

        thread_id = conversation_id
        try:
            messages = [HumanMessage(content=content)]
```

The changes are:
1. Remove `用户问题：{content}` from the system prompt (line 77 area)
2. The `messages = [HumanMessage(content=content)]` line stays as-is — user content is now always a separate HumanMessage, never embedded in the system prompt

- [ ] **Step 2: Verify**

```bash
cd server && uv run python -c "from ai.services.chat import stream_chat; print('chat service OK')"
```

- [ ] **Step 3: Commit**

```bash
git add server/ai/services/chat.py
git commit -m "fix: prevent prompt injection by separating user input from system prompt (#5)"
```

---

### Task 5: LLM Caching, HTTP Client Reuse, Timeout (#1, #3, #7)

**Files:**
- Modify: `server/ai/services/llm.py` — add LLM cache, HTTP client singleton, timeout params
- Modify: `server/ai/services/chat.py` — use cached LLM, refactor agent creation
- Modify: `server/ai/services/tools/grammar.py` — replace `_grammar_model` with `get_llm()`
- Modify: `server/ai/services/digest.py` — replace `create_deepseek` import and usage with `get_llm()`
- Modify: `server/ai/main.py` — close HTTP client on shutdown

- [ ] **Step 1: Rewrite llm.py with caching and HTTP client**

Replace the entire `server/ai/services/llm.py`:

```python
import logging
import httpx
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from ai.config import ai_settings

logger = logging.getLogger(__name__)

# --- LLM Cache ---
_llm_cache = {}


def get_llm(deep_think: bool = False) -> ChatDeepSeek:
    """获取缓存的 LLM 实例（按模型类型缓存）"""
    key = "reasoner" if deep_think else "normal"
    if key not in _llm_cache:
        if deep_think:
            _llm_cache[key] = ChatDeepSeek(
                api_key=ai_settings.deepseek_api_key,
                model=ai_settings.deepseek_reasoner_api_model,
                max_tokens=18000,
                streaming=True,
                timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
            )
        else:
            _llm_cache[key] = ChatDeepSeek(
                api_key=ai_settings.deepseek_api_key,
                model=ai_settings.deepseek_api_model,
                temperature=1.3,
                max_tokens=4396,
                streaming=True,
                timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
            )
    return _llm_cache[key]


# --- HTTP Client Singleton ---
_http_client = None


def get_http_client() -> httpx.AsyncClient:
    """获取共享的 HTTP 客户端（模块级单例）"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    return _http_client


async def close_http_client():
    """关闭 HTTP 客户端（应用关闭时调用）"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


# --- Checkpointer ---
_checkpointer_cm = None


async def create_checkpoint() -> AsyncPostgresSaver:
    """初始化 LangGraph checkpointer"""
    global _checkpointer_cm
    _checkpointer_cm = AsyncPostgresSaver.from_conn_string(ai_settings.ai_database_url)
    checkpointer = await _checkpointer_cm.__aenter__()
    await checkpointer.setup()
    return checkpointer


# --- Bocha Search ---
async def create_bocha_search(query: str, count: int = 10) -> str:
    """调用 Bocha 搜索 API（使用共享 HTTP 客户端）"""
    try:
        client = get_http_client()
        response = await client.post(
            ai_settings.bocha_search_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ai_settings.bocha_api_key}",
            },
            json={"query": query, "count": count, "summary": True},
        )
        data = response.json()
        values = data.get("data", {}).get("webPages", {}).get("value", [])

        if not values:
            return ""

        # 构建搜索结果，限制每条摘要 200 字符，总长度 5000 字符
        parts = []
        total_length = 0
        for item in values:
            summary = item.get('summary', '').replace(chr(10), '')[:200]
            if len(summary) >= 200:
                summary += "..."
            part = f"""标题：{item.get('name', '')}
链接：{item.get('url', '')}
摘要：{summary}
网站名称：{item.get('siteName', '')}"""
            if total_length + len(part) > 5000:
                break
            parts.append(part)
            total_length += len(part)

        # 用 XML 标签包裹，防止 prompt injection
        return "<search_results>\n" + "\n---\n".join(parts) + "\n</search_results>"
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.error(f"Bocha search failed: {e}")
        return ""
```

Key changes:
- `create_deepseek()` / `create_deepseek_reasoner()` replaced by `get_llm(deep_think)` with dict cache
- `httpx.AsyncClient` is now a module-level singleton via `get_http_client()`
- `close_http_client()` added for graceful shutdown
- All `ChatDeepSeek` instances get `timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)`
- `create_bocha_search` uses shared client instead of creating a new one each time

- [ ] **Step 2: Refactor chat.py to use cached LLM and agent**

In `server/ai/services/chat.py`, replace the imports and add agent caching logic:

Replace the import block (lines 10-15):
```python
# Before:
from ai.services.llm import (
    create_deepseek,
    create_deepseek_reasoner,
    create_checkpoint,
    create_bocha_search,
)

# After:
from ai.services.llm import (
    get_llm,
    create_checkpoint,
    create_bocha_search,
)
```

Replace the agent creation block in `stream_chat` (lines 83-96). Key change: only cache LLM (via `get_llm()`), create agent inside the retry loop so it gets the latest checkpointer. Agent creation is cheap (just assembly); LLM caching is the real performance win.

```python
# Before:
    # 选择模型
    model = create_deepseek_reasoner() if deep_think else create_deepseek()

    # 创建 agent（连接断开 / 历史脏数据时自动重试一次）
    for attempt in range(2):
        checkpointer = await get_checkpointer()
        # normal 角色使用工具，其他角色保持空工具
        tools = make_tools(user_id) if role == "normal" else []
        agent = create_react_agent(
            model=model,
            tools=tools,
            checkpointer=checkpointer,
            prompt=SystemMessage(content=prompt),  # 注入 system prompt
        )

# After:
    # 获取缓存的 LLM（按模型类型缓存，不按 role 缓存）
    model = get_llm(deep_think)

    # 创建 agent（连接断开 / 历史脏数据时自动重试一次）
    for attempt in range(2):
        checkpointer = await get_checkpointer()
        # normal 角色使用工具，其他角色保持空工具
        tools = make_tools(user_id) if role == "normal" else []
        agent = create_react_agent(
            model=model,
            tools=tools,
            checkpointer=checkpointer,
            prompt=SystemMessage(content=prompt),
        )
```

Note: `create_react_agent` stays inside the retry loop because checkpointer may change after `reset_checkpointer()`. The LLM instance is cached outside the loop since it's stateless.

Replace `generate_title` (lines 195-209) to use `get_llm()`:
```python
# Before:
async def generate_title(first_message: str) -> str:
    """用 AI 生成对话标题（15字以内），失败时降级为截取消息前15字。"""
    try:
        model = create_deepseek()
        response = await model.ainvoke([

# After:
async def generate_title(first_message: str) -> str:
    """用 AI 生成对话标题（15字以内），失败时降级为截取消息前15字。"""
    try:
        model = get_llm()
        response = await model.ainvoke([
```

Also remove the duplicate import that was already deleted in Task 1 (confirm it's gone).

- [ ] **Step 3: Update grammar.py to use cached LLM**

Replace `server/ai/services/tools/grammar.py`:

```python
# Before:
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from ai.services.llm import create_deepseek

# 语法检查专用 prompt — 直接要求自然语言输出，不要 JSON
GRAMMAR_PROMPT = """..."""

_grammar_model = None


@tool
async def grammar_check(text: str) -> str:
    """..."""
    if len(text) > 500:
        return "输入过长，请限制在 500 字符以内。"

    try:
        global _grammar_model
        if _grammar_model is None:
            _grammar_model = create_deepseek()
        messages = [
            HumanMessage(content=f"{GRAMMAR_PROMPT}\n\n待检查句子：{text}")
        ]
        response = await _grammar_model.ainvoke(messages)
        return response.content
    except Exception as e:
        return f"语法检查失败：{e}"

# After:
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from ai.services.llm import get_llm

# 语法检查专用 prompt — 直接要求自然语言输出，不要 JSON
GRAMMAR_PROMPT = """你是一个英语语法检查专家。请检查以下英文句子的语法错误。

输出格式要求（严格遵守）：
- 如果没有错误，直接输出：语法正确，没有发现错误。
- 如果有错误，按以下格式输出（纯文本，不要 JSON，不要 markdown）：
  语法错误：[用一句话总结错误]
  原句：[原始句子]
  修正：[修正后的句子]
  解释：[简短解释为什么错]

只输出上述内容，不要加任何前缀或额外文字。"""


@tool
async def grammar_check(text: str) -> str:
    """检查英语句子的语法错误，给出修正建议和错误原因解释。
    当用户输入英文句子要求检查、或用户在练习写作时使用此工具。
    不要用于查词或搜索信息。"""
    if len(text) > 500:
        return "输入过长，请限制在 500 字符以内。"

    try:
        model = get_llm()
        messages = [
            HumanMessage(content=f"{GRAMMAR_PROMPT}\n\n待检查句子：{text}")
        ]
        response = await model.ainvoke(messages)
        return response.content
    except Exception as e:
        return f"语法检查失败：{e}"
```

Changes: `_grammar_model` global variable and `create_deepseek` import removed, replaced with `get_llm()`.

- [ ] **Step 4: Update digest.py to use get_llm()**

In `server/ai/services/digest.py`, replace the import and usage:

```python
# Before (line 12):
from ai.services.llm import create_deepseek

# After:
from ai.services.llm import get_llm
```

```python
# Before (line 26):
    model = create_deepseek()

# After:
    model = get_llm()
```

- [ ] **Step 5: Add HTTP client shutdown to main.py lifespan**

In `server/ai/main.py`, add HTTP client cleanup to the lifespan shutdown:

```python
# Before:
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动定时任务"""
    start_scheduler()
    yield
    # 关闭时清理 checkpointer
    from ai.services.chat import reset_checkpointer
    await reset_checkpointer()

# After:
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动定时任务"""
    start_scheduler()
    yield
    # 关闭时清理资源
    from ai.services.chat import reset_checkpointer
    from ai.services.llm import close_http_client
    await reset_checkpointer()
    await close_http_client()
```

- [ ] **Step 6: Verify all changes**

```bash
cd server && uv run python -c "from ai.services.llm import get_llm, get_http_client, close_http_client; print('llm.py OK')"
cd server && uv run python -c "from ai.services.chat import stream_chat; print('chat.py OK')"
cd server && uv run python -c "from ai.services.tools.grammar import grammar_check; print('grammar.py OK')"
cd server && uv run python -c "from ai.services.digest import start_scheduler; print('digest.py OK')"
cd server && uv run python -c "from ai.main import ai_app; print('main.py OK')"
```

- [ ] **Step 7: Commit**

```bash
git add server/ai/services/llm.py server/ai/services/chat.py server/ai/services/tools/grammar.py server/ai/services/digest.py server/ai/main.py
git commit -m "perf: cache LLM instances, reuse HTTP client, add timeout (#1, #3, #7)"
```

---

### Task 6: Bug Fixes — Email Delay + Checkpointer (#9, #10)

**Files:**
- Modify: `server/ai/services/digest.py:99` — fix negative delay
- Modify: `server/ai/services/chat.py:44` — log checkpointer reset errors

- [ ] **Step 1: Fix email delay bug in digest.py**

In `server/ai/services/digest.py`, when `delay < 0`, add 86400 (next day) instead of setting to 0:

```python
# Before (lines 98-100):
                    delay = (target - datetime.now()).total_seconds()
                    if delay < 0:
                        delay = 0

# After:
                    delay = (target - datetime.now()).total_seconds()
                    if delay < 0:
                        delay += 86400  # 明天那个时间
```

- [ ] **Step 2: Log checkpointer reset errors in chat.py**

In `server/ai/services/chat.py`, change the silent `except Exception: pass` in `reset_checkpointer`:

```python
# Before (line 44):
            except Exception:
                pass  # 避免已关闭的连接池重复关闭报错

# After:
            except Exception as e:
                print(f"Checkpointer reset error: {e}")
```

- [ ] **Step 3: Verify**

```bash
cd server && uv run python -c "from ai.services.digest import handle_email_digest; print('digest.py OK')"
cd server && uv run python -c "from ai.services.chat import reset_checkpointer; print('chat.py OK')"
```

- [ ] **Step 4: Commit**

```bash
git add server/ai/services/digest.py server/ai/services/chat.py
git commit -m "fix: correct email delay calculation and log checkpointer errors (#9, #10)"
```

---

### Task 7: Chat History Pagination (#8)

**Files:**
- Modify: `server/ai/services/chat.py:152` — add limit parameter to `get_chat_history`

- [ ] **Step 1: Add limit to get_chat_history**

In `server/ai/services/chat.py`, add a `limit` parameter with default 50:

```python
# Before:
async def get_chat_history(conversation_id: str) -> list:

# After:
async def get_chat_history(conversation_id: str, limit: int = 50) -> list:
```

Then after the message filtering loop (before `return result`), add truncation:

```python
# Before:
            return result

# After:
            # 返回最近的 limit 条消息
            return result[-limit:] if len(result) > limit else result
```

- [ ] **Step 2: Verify**

```bash
cd server && uv run python -c "from ai.services.chat import get_chat_history; print('get_chat_history OK')"
```

- [ ] **Step 3: Commit**

```bash
git add server/ai/services/chat.py
git commit -m "feat: add limit parameter to get_chat_history (#8)"
```

---

### Task 8: Rate Limiting (#6)

**Files:**
- Modify: `server/pyproject.toml` — add slowapi dependency
- Modify: `server/ai/main.py` — configure rate limiter
- Modify: `server/ai/routers/chat.py` — apply rate limit to chat endpoint

- [ ] **Step 1: Add slowapi dependency**

In `server/pyproject.toml`, add `"slowapi>=0.1.9"` to the `dependencies` list.

Then run:
```bash
cd server && uv sync
```

- [ ] **Step 2: Create rate_limit.py module**

Create `server/ai/rate_limit.py` to avoid circular imports (ai.main imports routers, routers need limiter):

```python
"""速率限制配置（独立模块，避免循环导入）"""
import base64
import json as _json

from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_user_id_from_request(request) -> str:
    """从 JWT 中提取 userId（仅解码，不做签名验证——用于限流 key）"""
    try:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return get_remote_address(request)
        token = auth.split(" ")[1]
        # JWT payload 是第二段，base64url 解码
        payload_b64 = token.split(".")[1]
        # 补齐 padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("userId", get_remote_address(request))
    except Exception:
        return get_remote_address(request)


limiter = Limiter(key_func=_get_user_id_from_request)
```

Then in `server/ai/main.py`, register the limiter and exception handler:

```python
# Add to imports:
from ai.rate_limit import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# After ai_app = FastAPI(...):
ai_app.state.limiter = limiter
ai_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

- [ ] **Step 3: Apply rate limit to chat endpoint**

In `server/ai/routers/chat.py`, add the rate limit decorator. Note: import `limiter` from `ai.rate_limit` (not `ai.main`) to avoid circular imports — `ai.main` already imports from `ai.routers.chat`.

```python
# Add to imports:
from ai.rate_limit import limiter

# Add decorator to chat endpoint:
@router.post("")
@limiter.limit("20/minute")
async def chat(
    ...
```

Note: slowapi requires the `request: Request` parameter to be in the function signature. Add it:

Add `Request` to the existing FastAPI import at the top of the file:
```python
# Before (line 3):
from fastapi import APIRouter, Depends, HTTPException

# After:
from fastapi import APIRouter, Depends, HTTPException, Request
```

Then modify the endpoint signature:
```python
# Before:
@router.post("")
async def chat(
    data: ChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

# After:
@router.post("")
@limiter.limit("20/minute")
async def chat(
    request: Request,
    data: ChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
```

- [ ] **Step 4: Verify**

```bash
cd server && uv run python -c "from ai.rate_limit import limiter; print('rate_limit.py OK')"
cd server && uv run python -c "from ai.main import ai_app; print('main.py OK')"
```

- [ ] **Step 5: Commit**

```bash
git add server/pyproject.toml server/ai/rate_limit.py server/ai/main.py server/ai/routers/chat.py
git commit -m "feat: add rate limiting on chat endpoint (20/min per user) (#6)"
```

---

### Task 9: Logging (#11)

**Files:**
- Modify: `server/ai/main.py` — configure logging in lifespan
- Modify: `server/ai/services/chat.py` — replace print() with logger
- Modify: `server/ai/services/llm.py` — replace print() with logger
- Modify: `server/ai/services/digest.py` — replace print() with logger
- Modify: `server/ai/services/tools/grammar.py` — no print() to replace (already uses exception returns)

- [ ] **Step 1: Configure logging in main.py lifespan**

In `server/ai/main.py`, add logging config inside lifespan (before `yield`):

```python
import logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动定时任务"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    start_scheduler()
    yield
    ...
```

- [ ] **Step 2: Replace print() in chat.py**

Add logger at the top of `server/ai/services/chat.py`:

```python
import logging
logger = logging.getLogger(__name__)
```

Replace all `print()` calls:
- `print(f"Database connection error: {e}")` → `logger.error(f"Database connection error: {e}")`
- `print(f"Error getting chat history: {e}")` → `logger.error(f"Error getting chat history: {e}")`
- `traceback.print_exc()` → `logger.exception("Unexpected error in get_chat_history")`
- `print(f"Checkpointer reset error: {e}")` → `logger.warning(f"Checkpointer reset error: {e}")`

Also remove `import traceback` if no longer used.

- [ ] **Step 3: Verify llm.py logging (already done in Task 5)**

`server/ai/services/llm.py` was fully rewritten in Task 5 with `logger` already configured and `print()` replaced with `logger.error()`. No changes needed — just verify it's correct:

```bash
cd server && uv run python -c "from ai.services.llm import get_llm; print('llm.py OK')"
```

- [ ] **Step 4: Replace print() in digest.py**

Add logger at the top of `server/ai/services/digest.py`:

```python
import logging
logger = logging.getLogger(__name__)
```

Replace:
- `print("定时任务执行了")` → `logger.info("定时任务执行了")`
- `print(f"AI report generation failed: {e}")` → `logger.error(f"AI report generation failed: {e}")`
- `print("APScheduler started: daily digest at 00:00:00")` → `logger.info("APScheduler started: daily digest at 00:00:00")`

- [ ] **Step 5: Verify**

```bash
cd server && uv run python -c "from ai.main import ai_app; print('main.py OK')"
cd server && uv run python -c "from ai.services.chat import stream_chat; print('chat.py OK')"
cd server && uv run python -c "from ai.services.llm import get_llm; print('llm.py OK')"
cd server && uv run python -c "from ai.services.digest import start_scheduler; print('digest.py OK')"
```

- [ ] **Step 6: Commit**

```bash
git add server/ai/main.py server/ai/services/chat.py server/ai/services/llm.py server/ai/services/digest.py
git commit -m "refactor: replace print() with logging framework (#11)"
```

---

## Summary

| Task | Issues | Files Changed | Description |
|------|--------|--------------|-------------|
| 1 | #14, #15, #16 | main.py, chat.py, progress.py | Code cleanup |
| 2 | #4 | chat.py (router) | Conversation ownership validation |
| 3 | #12, #13 | conversation.py (schema + router) | Role validation, list limit |
| 4 | #5 | chat.py (service) | Prompt injection fix |
| 5 | #1, #3, #7 | llm.py, chat.py, grammar.py, digest.py, main.py | LLM cache, HTTP client, timeout |
| 6 | #9, #10 | digest.py, chat.py | Bug fixes |
| 7 | #8 | chat.py (service) | History pagination |
| 8 | #6 | pyproject.toml, rate_limit.py (new), main.py, chat.py (router) | Rate limiting |
| 9 | #11 | main.py, chat.py, llm.py, digest.py | Logging framework |


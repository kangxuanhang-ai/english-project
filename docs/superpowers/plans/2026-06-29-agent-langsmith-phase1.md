# Agent 现代化 Phase 1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AI 聊天与 digest 从 `create_react_agent` 迁移到 `create_agent`，接入可选 LangSmith tracing，**前端 SSE 协议与现有功能行为不变**。

**Architecture:** 新增 `agent_factory`、`middleware/chat_prompt`、`sse_adapter`、`chat_blocks` 四个模块；`stream_chat` 瘦身为编排层；SSE 映射沿用 `astream_events`（行为等价迁移，非 `agent.stream` 重写）。动态 prompt 经 `@dynamic_prompt` + 每请求 `ChatContext` 注入；LangSmith 仅在 `LANGCHAIN_API_KEY` 非空时启用。

**Tech Stack:** Python 3.12, FastAPI, LangChain 1.3.4, LangGraph 1.2.4, AsyncPostgresSaver, DeepSeek via langchain-deepseek

**设计文档:** [2026-06-29-agent-langsmith-upgrade-design.md](../specs/2026-06-29-agent-langsmith-upgrade-design.md)

**范围:** 仅 Phase 1（Phase 2 Prompt Hub、Phase 3 Eval 不在本计划内）

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `server/ai/services/chat_blocks.py` | Create | 从 `chat.py` 迁出：JSON 过滤、block 解析、`_coerce_tool_output_text`、`_ChatContentFilter` |
| `server/ai/services/middleware/__init__.py` | Create | 包初始化 |
| `server/ai/services/middleware/chat_prompt.py` | Create | `ChatContext` dataclass + `@dynamic_prompt` middleware |
| `server/ai/services/agent_factory.py` | Create | `create_agent` 封装 + agent 实例缓存 |
| `server/ai/services/sse_adapter.py` | Create | `astream_events` → legacy SSE 字符串 |
| `server/ai/services/chat.py` | Modify | 瘦身 `stream_chat`；history/title/checkpointer 保留；从 chat_blocks re-export 或 import |
| `server/ai/services/digest.py` | Modify | `create_agent` + 静态 system_prompt |
| `server/ai/services/tracing.py` | Create | LangSmith 环境变量 best-effort 初始化 |
| `server/ai/main.py` | Modify | lifespan 调用 `configure_langsmith_tracing()` |
| `server/ai/config.py` | Modify | 可选 `langchain_api_key` / `langchain_project` 字段 |
| `server/.env.example` | Modify | LangSmith 变量说明 |
| `server/scripts/smoke_chat_agent.py` | Create | Phase 1 冒烟：agent 创建、history、SSE 事件类型 |
| `AGENTS.md` / `CLAUDE.md` | Modify | agent 架构描述 |

**不修改:** `apps/web/**`、`server/ai/routers/recommend.py`、`server/ai/services/tools/**`（除非 import 路径变化）

---

## Task 1: LangSmith tracing 可选初始化

**Files:**
- Create: `server/ai/services/tracing.py`
- Modify: `server/ai/config.py`
- Modify: `server/ai/main.py`
- Modify: `server/.env.example`

- [ ] **Step 1: 扩展 AISettings**

在 `server/ai/config.py` 的 `AISettings` 末尾添加：

```python
    langchain_api_key: str = Field(default="", alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="english-chat", alias="LANGCHAIN_PROJECT")
```

- [ ] **Step 2: 创建 tracing.py**

```python
# server/ai/services/tracing.py
import logging
import os

from ai.config import ai_settings

logger = logging.getLogger(__name__)


def configure_langsmith_tracing() -> None:
    """仅当 API key 存在时启用 LangSmith tracing；失败不抛异常。"""
    key = (ai_settings.langchain_api_key or os.getenv("LANGCHAIN_API_KEY") or "").strip()
    if not key:
        logger.info("LangSmith tracing disabled: LANGCHAIN_API_KEY not set")
        return
    os.environ.setdefault("LANGCHAIN_API_KEY", key)
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    project = (ai_settings.langchain_project or "english-chat").strip()
    os.environ.setdefault("LANGCHAIN_PROJECT", project)
    logger.info("LangSmith tracing enabled for project=%s", project)
```

- [ ] **Step 3: 在 ai/main.py lifespan 开头调用**

在 `logging.basicConfig(...)` 之后、`start_scheduler()` 之前添加：

```python
from ai.services.tracing import configure_langsmith_tracing

configure_langsmith_tracing()
```

- [ ] **Step 4: 更新 .env.example**

在文件末尾追加（与 spec 一致）：

```env
# LangSmith（可选；仅当 LANGCHAIN_API_KEY 非空时 AI 服务自动启用 tracing）
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=english-chat
```

- [ ] **Step 5: 验证**

```bash
cd server
uv run python -c "from ai.services.tracing import configure_langsmith_tracing; configure_langsmith_tracing(); import os; print('tracing', os.getenv('LANGCHAIN_TRACING_V2'))"
```

Expected（无 key）: 日志含 `disabled`，`tracing None`

- [ ] **Step 6: 提交**

```bash
git add server/ai/services/tracing.py server/ai/config.py server/ai/main.py server/.env.example
git commit -m "feat(ai): add optional LangSmith tracing bootstrap"
```

---

## Task 2: 抽出 chat_blocks 共享模块

**Files:**
- Create: `server/ai/services/chat_blocks.py`
- Modify: `server/ai/services/chat.py`

- [ ] **Step 1: 创建 chat_blocks.py**

将 `chat.py` 中以下符号**原样剪切**到 `chat_blocks.py`（保留中文注释）：

- 常量/函数：`_JSON_INSTRUCTION_LEAK` 至 `_strip_recommend_json_buffer`
- 类：`_ChatContentFilter`
- 函数：`_coerce_tool_output_text`、`_extract_grammar_block`、`_extract_recommend_block`、`_parse_purchase_json`、`_extract_purchase_block`、`_parse_recommend_json`、`_parse_recommend_from_agent_text`

文件头：

```python
# server/ai/services/chat_blocks.py
"""聊天 SSE 与历史还原共用的 block 解析与 JSON 过滤。"""
import json
import re
# ... 其余 import 按剪切内容补齐
```

- [ ] **Step 2: 修改 chat.py 改为 import**

删除已迁出代码，添加：

```python
from ai.services.chat_blocks import (
    ChatContentFilter,
    coerce_tool_output_text,
    extract_grammar_block,
    extract_purchase_block,
    extract_recommend_block,
    fold_messages_for_history,
)
```

同时将 `_ChatContentFilter` 重命名为公开 `ChatContentFilter`，`_coerce_tool_output_text` → `coerce_tool_output_text`，`_extract_*` → `extract_*`（去掉 leading underscore，便于 sse_adapter 使用）。

`_fold_messages_for_history` 也迁入 `chat_blocks.py` 并重命名为 `fold_messages_for_history`（依赖 `extract_*` 与 `_tool_summary`，一并迁入）。

- [ ] **Step 3: 更新 get_chat_history**

```python
folded = fold_messages_for_history(messages)
```

- [ ] **Step 4: 验证 import**

```bash
cd server
uv run python -c "from ai.services.chat_blocks import ChatContentFilter, extract_recommend_block; print('ok')"
uv run python -c "from ai.services.chat import get_chat_history; print('ok')"
```

Expected: 两次均打印 `ok`，无 ImportError

- [ ] **Step 5: 提交**

```bash
git add server/ai/services/chat_blocks.py server/ai/services/chat.py
git commit -m "refactor(ai): extract chat block parsing into chat_blocks module"
```

---

## Task 3: dynamic_prompt middleware

**Files:**
- Create: `server/ai/services/middleware/__init__.py`
- Create: `server/ai/services/middleware/chat_prompt.py`

- [ ] **Step 1: 创建 middleware 包**

`server/ai/services/middleware/__init__.py`:

```python
from ai.services.middleware.chat_prompt import ChatContext, chat_dynamic_prompt

__all__ = ["ChatContext", "chat_dynamic_prompt"]
```

- [ ] **Step 2: 创建 chat_prompt.py**

```python
# server/ai/services/middleware/chat_prompt.py
from dataclasses import dataclass, field

from langchain.agents.middleware import ModelRequest, dynamic_prompt


@dataclass
class ChatContext:
    """每请求传入 create_agent astream 的 runtime context。"""

    role: str = "normal"
    base_prompt: str = ""
    search_block: str = ""
    progress_block: str = ""


@dynamic_prompt
def chat_dynamic_prompt(request: ModelRequest) -> str:
    ctx: ChatContext | None = request.runtime.context  # type: ignore[assignment]
    if ctx is None:
        return "You are a helpful assistant."
    parts = [ctx.base_prompt, ctx.search_block, ctx.progress_block]
    return "".join(p for p in parts if p)
```

- [ ] **Step 3: 验证 middleware**

```bash
cd server
uv run python -c "
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest
from ai.services.llm import get_llm
from ai.services.middleware.chat_prompt import ChatContext, chat_dynamic_prompt

model = get_llm(False)
agent = create_agent(model=model, tools=[], middleware=[chat_dynamic_prompt], context_schema=ChatContext)
print('agent ok', type(agent))
"
```

Expected: `agent ok <class '...CompiledStateGraph...'>`

- [ ] **Step 4: 提交**

```bash
git add server/ai/services/middleware/
git commit -m "feat(ai): add ChatContext dynamic_prompt middleware"
```

---

## Task 4: agent_factory

**Files:**
- Create: `server/ai/services/agent_factory.py`

- [ ] **Step 1: 实现 agent_factory.py**

```python
# server/ai/services/agent_factory.py
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from ai.services.middleware.chat_prompt import chat_dynamic_prompt

# Agent 缓存：normal / web_search 不缓存（与 chat.py 原逻辑一致）
_agent_cache: dict[tuple, object] = {}


def agent_cache_key(role: str, deep_think: bool, web_search: bool) -> tuple | None:
    if web_search:
        return None
    if role == "normal":
        return None
    return (role, deep_think)


def get_or_create_agent(
    *,
    model: BaseChatModel,
    tools: list,
    checkpointer,
    cache_key: tuple | None,
) -> object:
    if cache_key and cache_key in _agent_cache:
        return _agent_cache[cache_key]

    agent = create_agent(
        model=model,
        tools=tools,
        checkpointer=checkpointer,
        middleware=[chat_dynamic_prompt],
        context_schema=__import__(
            "ai.services.middleware.chat_prompt", fromlist=["ChatContext"]
        ).ChatContext,
    )
    if cache_key:
        _agent_cache[cache_key] = agent
    return agent


def clear_agent_cache() -> None:
    _agent_cache.clear()
```

（实现时可将 `ChatContext` 改为顶部直接 import，避免 `__import__` 花招。）

- [ ] **Step 2: 验证 factory + checkpointer**

```bash
cd server
uv run python -c "
import asyncio, sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def t():
    from langchain_core.messages import HumanMessage
    from ai.services.llm import get_llm, create_checkpoint
    from ai.services.agent_factory import get_or_create_agent
    from ai.services.middleware.chat_prompt import ChatContext

    cp = await create_checkpoint()
    model = get_llm(False)
    agent = get_or_create_agent(model=model, tools=[], checkpointer=cp, cache_key=('master', False))
    tid = 'factory-smoke-1'
    await cp.adelete_thread(tid)
    async for _ in agent.astream_events(
        {'messages': [HumanMessage(content='hi')]},
        config={'configurable': {'thread_id': tid}},
        context=ChatContext(role='master', base_prompt='You are master.'),
        version='v2',
    ):
        pass
    st = await cp.aget({'configurable': {'thread_id': tid}})
    print('msgs', len(st['channel_values']['messages']))
    await cp.adelete_thread(tid)

asyncio.run(t())
"
```

Expected: `msgs 2`

- [ ] **Step 3: 提交**

```bash
git add server/ai/services/agent_factory.py
git commit -m "feat(ai): add create_agent factory with role-based cache"
```

---

## Task 5: sse_adapter（astream_events → legacy SSE）

**Files:**
- Create: `server/ai/services/sse_adapter.py`

- [ ] **Step 1: 实现 stream_legacy_sse 异步生成器**

```python
# server/ai/services/sse_adapter.py
import json
from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage

from ai.services.chat_blocks import (
    ChatContentFilter,
    coerce_tool_output_text,
    extract_grammar_block,
    extract_purchase_block,
    extract_recommend_block,
)
from ai.services.middleware.chat_prompt import ChatContext


async def stream_legacy_sse(
    agent,
    *,
    content: str,
    thread_id: str,
    context: ChatContext,
) -> AsyncIterator[str]:
    """将 agent.astream_events 映射为现有前端 SSE JSON 行。"""
    chat_filter = ChatContentFilter()
    messages = [HumanMessage(content=content)]

    async for event in agent.astream_events(
        {"messages": messages},
        config={"configurable": {"thread_id": thread_id}},
        context=context,
        version="v2",
    ):
        kind = event.get("event")
        if kind == "on_tool_start":
            tool_name = event.get("name", "")
            tool_input = event.get("data", {}).get("input", "")
            if isinstance(tool_input, dict):
                tool_input = json.dumps(tool_input, ensure_ascii=False)
            call_id = str(event.get("run_id", ""))
            yield _sse(
                {
                    "type": "tool",
                    "id": call_id,
                    "tool": tool_name,
                    "input": str(tool_input),
                }
            )
        elif kind == "on_tool_end":
            tool_name = event.get("name", "")
            tool_output_raw = event.get("data", {}).get("output", "")
            tool_output_text = coerce_tool_output_text(tool_output_raw)
            call_id = str(event.get("run_id", ""))
            payload: dict = {
                "type": "tool_result",
                "id": call_id,
                "tool": tool_name,
                "output": tool_output_text,
            }
            if tool_name == "course_recommendation":
                block = extract_recommend_block(tool_output_text)
                if block:
                    payload["recommendBlock"] = block
                    payload["output"] = json.dumps(block, ensure_ascii=False)
            elif tool_name == "grammar_check":
                block = extract_grammar_block(tool_output_text)
                if block:
                    payload["grammarBlock"] = block
            elif tool_name == "course_purchase":
                block = extract_purchase_block(tool_output_text)
                if block:
                    payload["purchaseBlock"] = block
                    payload["output"] = json.dumps(block, ensure_ascii=False)
            yield _sse(payload)
        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if not chunk:
                continue
            reasoning = getattr(chunk, "additional_kwargs", {}).get("reasoning_content", "")
            if reasoning:
                yield _sse(
                    {"content": reasoning, "role": "ai", "type": "reasoning"}
                )
            content_text = chunk.content if hasattr(chunk, "content") else ""
            if isinstance(content_text, list):
                content_text = "".join(
                    b if isinstance(b, str) else b.get("text", "")
                    for b in content_text
                    if isinstance(b, (str, dict))
                )
            if content_text:
                content_text = chat_filter.feed(str(content_text))
                if content_text:
                    yield _sse(
                        {"content": content_text, "role": "ai", "type": "chat"}
                    )

    yield _sse({"type": "done"})


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
```

- [ ] **Step 2: 验证 SSE 行格式**

```bash
cd server
uv run python -c "
import asyncio, sys, json
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def t():
    from ai.services.llm import get_llm, create_checkpoint
    from ai.services.agent_factory import get_or_create_agent
    from ai.services.middleware.chat_prompt import ChatContext
    from ai.services.sse_adapter import stream_legacy_sse

    cp = await create_checkpoint()
    model = get_llm(False)
    agent = get_or_create_agent(model=model, tools=[], checkpointer=cp, cache_key=None)
    tid = 'sse-smoke-1'
    await cp.adelete_thread(tid)
    types = []
    async for line in stream_legacy_sse(
        agent, content='say hi', thread_id=tid,
        context=ChatContext(base_prompt='You are helpful.'),
    ):
        if line.startswith('data:'):
            types.append(json.loads(line[5:].strip()).get('type'))
    print('types', types)

asyncio.run(t())
"
```

Expected: 含 `chat` 与 `done`

- [ ] **Step 3: 提交**

```bash
git add server/ai/services/sse_adapter.py
git commit -m "feat(ai): add astream_events to legacy SSE adapter"
```

---

## Task 6: 重构 stream_chat

**Files:**
- Modify: `server/ai/services/chat.py`

- [ ] **Step 1: 删除 create_react_agent import 与 _agent_cache**

移除：

```python
from langgraph.prebuilt import create_react_agent
_agent_cache: dict[tuple, object] = {}
def _agent_cache_key(...):
```

改为：

```python
from ai.services.agent_factory import agent_cache_key, get_or_create_agent
from ai.services.middleware.chat_prompt import ChatContext
from ai.services.sse_adapter import stream_legacy_sse
```

- [ ] **Step 2: 重写 stream_chat 主体**

prompt 组装逻辑（auto web search、Bocha、progress snapshot）**保持不动**，但改为写入 `ChatContext` 字段而非拼接后传入 `SystemMessage`：

```python
    base_prompt = prompt_obj["prompt"]
    search_block = ""
    progress_block = ""

    # ... 现有 web_search / snapshot 逻辑 ...
    # 原先 prompt += search 的部分改为 search_block += ...
    # 原先 prompt += snapshot 改为 progress_block = snapshot

    ctx = ChatContext(
        role=role,
        base_prompt=base_prompt,
        search_block=search_block,
        progress_block=progress_block,
    )

    for attempt in range(2):
        checkpointer = await get_checkpointer()
        tools = make_tools_by_role(...)
        cache_key = agent_cache_key(role, deep_think, web_search)
        agent = get_or_create_agent(
            model=model,
            tools=tools,
            checkpointer=checkpointer,
            cache_key=cache_key,
        )
        emitted_terminal = False
        emitted_error = False
        will_retry = False
        try:
            async for chunk in stream_legacy_sse(
                agent,
                content=content,
                thread_id=conversation_id,
                context=ctx,
            ):
                yield chunk
            emitted_terminal = True
            break
        except OperationalError as e:
            # ... 保持原有 retry / error yield 逻辑不变 ...
        except ValueError as e:
            # ... 保持 poisoned thread adelete_thread 逻辑不变 ...
        except Exception as e:
            # ... 保持原有逻辑 ...
        finally:
            # ... 保持 stream interrupted 逻辑不变 ...
```

**注意:** `stream_legacy_sse` 已在正常结束时 yield `done`；`stream_chat` 内**不要再** duplicate yield `done`（删除原 390 行附近的 `yield done`）。

- [ ] **Step 3: 确认 get_chat_history / generate_title 未破坏**

`get_chat_history` 仍用 checkpointer + `fold_messages_for_history`。  
`generate_title` 仍直接 `model.ainvoke`，不经过 agent。

- [ ] **Step 4: 启动 AI 服务 smoke**

```bash
cd server
uv run python -c "from ai.services.chat import stream_chat; print('import ok')"
```

Expected: `import ok`

- [ ] **Step 5: 提交**

```bash
git add server/ai/services/chat.py
git commit -m "feat(ai): migrate stream_chat to create_agent and sse_adapter"
```

---

## Task 7: 迁移 digest.py

**Files:**
- Modify: `server/ai/services/digest.py`

- [ ] **Step 1: 替换 create_react_agent**

删除：

```python
from langgraph.prebuilt import create_react_agent
```

添加：

```python
from langchain.agents import create_agent
```

将：

```python
agent = create_react_agent(model=model, tools=[])
```

改为：

```python
agent = create_agent(
    model=model,
    tools=[],
    system_prompt=(
        "你是英语学习平台的报告助手。"
        "根据用户今日学习数据，生成简短、友好的中文单词记忆报告，使用 Markdown 格式。"
    ),
)
```

`agent.ainvoke` 调用保持不变（仍传 `{"messages": [{"role": "user", "content": report_prompt}]}`）。

- [ ] **Step 2: 验证 digest import**

```bash
cd server
uv run python -c "from ai.services.digest import handle_email_digest; print('ok')"
```

- [ ] **Step 3: 提交**

```bash
git add server/ai/services/digest.py
git commit -m "feat(ai): migrate digest agent to create_agent"
```

---

## Task 8: smoke_chat_agent.py

**Files:**
- Create: `server/scripts/smoke_chat_agent.py`

- [ ] **Step 1: 创建冒烟脚本**

```python
#!/usr/bin/env python3
"""Phase 1: create_agent + checkpointer + SSE 事件类型冒烟。"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage

from ai.services.agent_factory import get_or_create_agent
from ai.services.chat import get_chat_history
from ai.services.llm import create_checkpoint, get_llm
from ai.services.middleware.chat_prompt import ChatContext
from ai.services.sse_adapter import stream_legacy_sse


async def main() -> int:
    cp = await create_checkpoint()
    model = get_llm(False)
    tid = "smoke-phase1-cross-compat"
    await cp.adelete_thread(tid)

    # 1) 旧 agent 写入一条消息
    old = create_react_agent(
        model=model, tools=[], checkpointer=cp,
        prompt=SystemMessage(content="legacy"),
    )
    await old.ainvoke(
        {"messages": [HumanMessage(content="legacy hello")]},
        config={"configurable": {"thread_id": tid}},
    )

    # 2) 新 agent 追加 + SSE
    agent = get_or_create_agent(model=model, tools=[], checkpointer=cp, cache_key=("master", False))
    types: list[str] = []
    async for line in stream_legacy_sse(
        agent,
        content="new hello",
        thread_id=tid,
        context=ChatContext(role="master", base_prompt="You are master."),
    ):
        if line.startswith("data:"):
            types.append(json.loads(line[5:].strip()).get("type", ""))

    assert "done" in types, f"missing done: {types}"

    # 3) history 可读
    hist = await get_chat_history(tid, limit=50)
    assert len(hist["messages"]) >= 2, hist

    await cp.adelete_thread(tid)
    print("smoke_chat_agent: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

- [ ] **Step 2: 运行冒烟**

```bash
cd server
uv run python scripts/smoke_chat_agent.py
```

Expected: `smoke_chat_agent: PASS`

- [ ] **Step 3: 提交**

```bash
git add server/scripts/smoke_chat_agent.py
git commit -m "test(ai): add smoke script for create_agent phase1"
```

---

## Task 9: 文档更新

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: 更新 AI Chat Architecture 段落**

将 `LangGraph create_react_agent` 改为：

```markdown
LangChain `create_agent`（经 `agent_factory`）+ `@dynamic_prompt` middleware + PostgresCheckpointer。
SSE 经 `sse_adapter` 将 `astream_events` 映射为 legacy 事件类型。可选 LangSmith tracing（`LANGCHAIN_API_KEY`）。
```

- [ ] **Step 2: 提交**

```bash
git add AGENTS.md CLAUDE.md
git commit -m "docs: update agent architecture for create_agent migration"
```

---

## Task 10: 手动验收清单（Phase 1 完成门）

在本地启动 `pnpm ai` + `pnpm web`，使用已登录用户逐项验证（对照 spec 4.1.5）：

- [ ] **normal — 查词:** 「abandon 什么意思」→ 出现 tool 状态 + 释义
- [ ] **normal — 语法:** 提交英语句子 + 深度思考 → `grammarBlock` 卡片
- [ ] **normal — 推荐:** 「推荐一门课」→ `recommendBlock` 卡片
- [ ] **normal — 购课:** 「买第一个」→ 流结束后购课确认弹窗
- [ ] **normal — 自动联网:** 「今天北京天气」→ 无需手动开联网
- [ ] **normal — 知识库:** 平台内事实问题 → `knowledge_search` tool
- [ ] **master / business / qilinge / xiaoman:** 各发一条消息，回复正常
- [ ] **oral:** 英文句子 → 仅 grammar 相关行为
- [ ] **多轮:** 同一会话第二轮能引用上下文
- [ ] **历史:** 刷新页面后 history API 还原卡片与正文
- [ ] **reasoner:** 深度思考开关 → 前端出现 reasoning 流
- [ ] **LangSmith（若已配 key）:** `english-chat` project 可见 trace

全部通过后 Phase 1 完成；**不要**在本阶段启动 Phase 2 Prompt Hub。

- [ ] **Step: 最终提交（若有未提交改动）**

```bash
git status
```

---

## Plan Self-Review

| Spec 要求 | 对应 Task |
|-----------|-----------|
| create_agent 替换 | Task 4, 6, 7 |
| astream_events SSE 不变 | Task 5, 6 |
| dynamic_prompt + ChatContext | Task 3, 6 |
| LangSmith 可选 tracing | Task 1 |
| digest 迁移 | Task 7 |
| 旧 thread 兼容 | Task 8 smoke |
| 验收清单 | Task 10 |
| chat_blocks 不丢失 JSON 过滤 | Task 2, 5 |
| 不在 Phase 1 改前端 | File Structure 约束 |

**Placeholder scan:** 无 TBD；各 Task 含完整路径与代码骨架。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-29-agent-langsmith-phase1.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每个 Task 派一个 subagent，Task 间人工 review  
2. **Inline Execution** — 本会话按 Task 1→10 顺序直接实现，每 2–3 个 Task 汇报一次

**Which approach?**

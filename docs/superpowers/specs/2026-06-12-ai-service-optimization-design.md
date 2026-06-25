# AI Service Optimization Design

Date: 2026-06-12

## Overview

优化 AI 服务（`server/ai/`）的安全性、性能和代码质量。基于 Codex 和 Claude 的联合分析，修复 16 个问题（跳过 #17 Prompt 硬编码和 #18 可观测性，当前阶段不需要）。

## Scope

涉及文件：
- `server/ai/routers/chat.py` — 归属校验
- `server/ai/routers/conversation.py` — 角色验证、对话列表限制
- `server/ai/services/chat.py` — LLM/Agent 缓存、Prompt Injection 修复、异常处理
- `server/ai/services/llm.py` — LLM 缓存、HTTP client 复用、timeout
- `server/ai/services/digest.py` — 邮件延迟 bug
- `server/ai/services/tools/grammar.py` — 删除全局变量（改用缓存的 LLM）
- `server/ai/services/tools/progress.py` — SQLAlchemy 风格
- `server/ai/main.py` — logging 配置、删除无用 import
- `server/ai/schemas/conversation.py` — Literal 类型约束
- `server/ai/rate_limit.py` — 新建，速率限制配置（独立模块避免循环导入）
- `server/pyproject.toml` — 新增 slowapi 依赖

## Design

### 1. Security Fixes

#### #4 对话归属校验

`routers/chat.py` 的 `chat` 和 `history` 端点，当 conversation 不存在或不属于当前用户时返回 404。

**chat 端点**：在查询 conversation 后，如果为 None 则 raise HTTPException(404)。这会阻止后续的 stream_chat 执行。

**history 端点**：新增归属校验。当前代码直接调用 `get_chat_history(conversationId)`，没有任何校验。改为先查 Conversation 表验证归属，再调用 `get_chat_history`。

#### #5 Prompt Injection 修复

`services/chat.py` 的 `stream_chat` 中，将用户输入从 system prompt 移到 HumanMessage：

- 当 `web_search=True` 且搜索结果非空时：system prompt = 原始 prompt + 搜索结果上下文，用户 content 作为独立的 HumanMessage
- 当 `web_search=False` 或搜索结果为空时：system prompt = 原始 prompt，用户 content 作为 HumanMessage
- `astream_events` 的 messages 参数始终为 `[HumanMessage(content=content)]`

#### #6 速率限制

使用 `slowapi` 库，按用户 ID（从 JWT token 中提取）限流。

- 限制：每用户每分钟 20 次 `/ai/v1/chat` 请求
- key_func：自定义函数，从 `Authorization` header 中解码 JWT payload 提取 userId（仅解码 payload，不做签名验证——限流 key 不需要密码学保证）。如果 header 缺失或格式错误，回退到 IP 地址。
- 返回 429 Too Many Requests
- 新增依赖：`slowapi`（加入 `pyproject.toml`）

### 2. Performance Fixes

#### #1 LLM/Agent 缓存

**LLM 缓存**：模块级字典 `_llm_cache`，key 为 model type（"normal" 或 "reasoner"）。所有角色共用。

```python
_llm_cache = {}

def get_llm(deep_think: bool = False) -> ChatDeepSeek:
    key = "reasoner" if deep_think else "normal"
    if key not in _llm_cache:
        _llm_cache[key] = create_deepseek_reasoner() if deep_think else create_deepseek()
    return _llm_cache[key]
```

**Agent 不缓存**：agent 依赖 checkpointer（可能在重试时被 reset），且 normal 角色的 tools 绑定了 user_id。agent 创建成本低（只是组装），不值得缓存。在 retry 循环内每次创建。

`generate_title` 也改为使用 `get_llm()` 而不是直接调用 `create_deepseek()`。

`tools/grammar.py` 的 `_grammar_model` 全局变量删除，改为调用 `get_llm()`，不再独立管理模型实例。grammar_check 工具中的 `global _grammar_model` 和相关的 if 判断全部移除，直接使用缓存的 LLM。

#### #3 HTTP Client 复用

`llm.py` 中的 `httpx.AsyncClient` 改为模块级单例：

```python
_http_client = None

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    return _http_client
```

在 `ai/main.py` 的 lifespan shutdown 中调用 `_http_client.aclose()` 关闭连接。

#### #7 LLM Timeout

`ChatDeepSeek` 构造时传入 timeout 参数：

```python
ChatDeepSeek(
    ...,
    timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
)
```

- connect=10s：连接建立超时
- read=60s：流式读取超时（给 streaming 响应足够时间）
- write=10s：请求发送超时
- pool=10s：连接池获取超时

#### #8 对话历史分页

`get_chat_history` 加 `limit` 参数，默认 50。在过滤后的消息列表末尾截取最近 N 条。

### 3. Bug Fixes

#### #9 邮件延迟 bug

`digest.py` 中 `delay < 0` 时改为 `delay += 86400`（明天那个时间），而不是置为 0。

#### #10 Checkpointer 异常处理

`reset_checkpointer` 中 `except Exception: pass` 改为 `except Exception as e: print(f"Checkpointer reset error: {e}")`。后续 #11 完成后改为 logging。

### 4. Code Quality

#### #11 Logging

- 在 `ai/main.py` 的 lifespan（yield 之前）配置 `logging.basicConfig(level=logging.INFO)`
- 各模块顶部加 `logger = logging.getLogger(__name__)`
- 所有 `print()` 替换为 `logger.info()` / `logger.error()` / `logger.warning()`
- 涉及文件：`chat.py`、`llm.py`、`digest.py`、`grammar.py`、`main.py`

#### #12 角色验证

`schemas/conversation.py` 的 `CreateConversationRequest.role` 改为：
```python
from typing import Literal
role: Literal['normal', 'master', 'business', 'qilinge', 'xiaoman']
```

#### #13 Conversation List 限制

`routers/conversation.py` 的 `list_conversations` 查询加 `.limit(200)`。

#### #14 无用 import

删除 `ai/main.py` 的 `import selectors`。

#### #15 重复 import

删除 `ai/services/chat.py` `generate_title` 函数内的 `from langchain_core.messages import HumanMessage`（文件顶部已导入）。

#### #16 SQLAlchemy 风格

`tools/progress.py` 的 `is_master == True` 改为 `is_master.is_(True)`。

## Implementation Order

1. #14, #15, #16 — 代码清理（无依赖）
2. #4 — 对话归属校验（最高优先级安全修复）
3. #12, #13 — Schema 和查询修改
4. #5 — Prompt Injection 修复
5. #1, #3, #7 — LLM 缓存、HTTP client、timeout（相互关联）
6. #9, #10 — Bug 修复
7. #8 — 历史分页
8. #6 — 速率限制（需要新增依赖）
9. #11 — Logging（全局替换，放最后避免冲突）

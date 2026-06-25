# Agent 工具化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给现有 Chat 的 `normal` 角色注册 4 个 LangChain Tools（查词、语法检查、Web 搜索、学习进度查询），使其从对话机器人进化为英语学习 Agent。

**Architecture:** 在 `server/ai/services/tools/` 下新建 4 个工具模块，通过 `@tool` 装饰器定义 LangChain 工具。工具通过 `app.database.async_session` 创建独立 DB 会话查询数据。修改 `stream_chat()` 将工具列表传入 `create_react_agent`。前端扩展 SSE 事件类型展示工具调用过程。

**Tech Stack:** Python 3.12+, FastAPI, LangChain, LangGraph, SQLAlchemy async, Vue 3, TypeScript

---

## 文件结构

### 新增文件
| 文件 | 职责 |
|------|------|
| `server/ai/services/tools/__init__.py` | 导出工具列表 `all_tools` |
| `server/ai/services/tools/word.py` | 查词工具 — 查询 WordBook 表 |
| `server/ai/services/tools/grammar.py` | 语法检查工具 — 调用 DeepSeek LLM |
| `server/ai/services/tools/search.py` | Web 搜索工具 — 封装 Bocha API |
| `server/ai/services/tools/progress.py` | 学习进度查询 — 查询 User/WordBookRecord/CourseRecord |

### 修改文件
| 文件 | 改动 |
|------|------|
| `server/ai/services/chat.py:69-71` | `tools=[]` 改为 `tools=all_tools`（仅 normal 角色） |
| `server/ai/services/chat.py:78-96` | SSE 事件循环增加 `on_tool_start` / `on_tool_end` 处理 |
| `server/ai/services/prompt.py:2-7` | normal 角色的 prompt 增加工具使用指引 |
| `packages/common/chat/index.ts:3-9` | 扩展 `ChatMessageType` 和 `ChatMessage` |
| `apps/web/src/views/Chat/index.vue:24-35` | `sendMessage` 增加 tool/tool_result 事件处理 |
| `apps/web/src/views/Chat/components/Bubble.vue:4-23` | 新增工具调用/结果气泡样式 |

---

## Task 1：查词工具 `word_lookup`

**Files:**
- Create: `server/ai/services/tools/word.py`
- Create: `server/ai/services/tools/__init__.py`

- [ ] **Step 1: 创建查词工具文件**

创建 `server/ai/services/tools/word.py`：

```python
import json
from langchain_core.tools import tool
from sqlalchemy import select
from app.database import async_session
from app.models.word_book import WordBook, WordBookRecord


@tool
async def word_lookup(word: str) -> str:
    """查询英语单词的详细信息，包括音标、中文释义、例句。
    当用户询问某个单词的意思、用法、拼写时使用此工具。
    不要用于检查语法或搜索互联网信息。"""
    async with async_session() as session:
        # 查询单词
        result = await session.execute(
            select(WordBook).where(WordBook.word == word.lower().strip())
        )
        entry = result.scalar_one_or_none()

        if not entry:
            return json.dumps({"error": f"未找到单词 '{word}'"}, ensure_ascii=False)

        return json.dumps({
            "word": entry.word,
            "phonetic": entry.phonetic,
            "definition": entry.definition,
            "translation": entry.translation,
            "pos": entry.pos,
            "exchange": entry.exchange,
        }, ensure_ascii=False)
```

- [ ] **Step 2: 创建工具导出文件**

创建 `server/ai/services/tools/__init__.py`：

```python
from .word import word_lookup

all_tools = [word_lookup]
```

> 后续每完成一个工具，都会更新此文件。

- [ ] **Step 3: 验证导入无语法错误**

```bash
cd server && uv run python -c "from ai.services.tools import all_tools; print(f'Tools loaded: {len(all_tools)}')"
```

Expected: `Tools loaded: 1`

- [ ] **Step 4: Commit**

```bash
git add server/ai/services/tools/
git commit -m "feat(agent): add word_lookup tool"
```

---

## Task 2：Web 搜索工具 `web_search`

**Files:**
- Create: `server/ai/services/tools/search.py`
- Modify: `server/ai/services/tools/__init__.py`

- [ ] **Step 1: 创建搜索工具文件**

创建 `server/ai/services/tools/search.py`：

```python
import json
from langchain_core.tools import tool
from ai.services.llm import create_bocha_search


@tool
async def web_search(query: str) -> str:
    """搜索互联网获取实时信息。仅在以下情况使用：
    1. 用户明确要求搜索
    2. 问题需要最新信息（如新闻、最新术语）
    3. 问题超出英语学习范畴
    查词、语法问题请优先使用 word_lookup 和 grammar_check。"""
    try:
        result = await create_bocha_search(query)
        if not result or not result.strip():
            return json.dumps({"error": "未找到相关搜索结果"}, ensure_ascii=False)
        return result
    except Exception as e:
        return json.dumps({"error": f"搜索失败: {e}"}, ensure_ascii=False)
```

- [ ] **Step 2: 更新工具导出**

修改 `server/ai/services/tools/__init__.py`：

```python
from .word import word_lookup
from .search import web_search

all_tools = [word_lookup, web_search]
```

- [ ] **Step 3: 验证导入**

```bash
cd server && uv run python -c "from ai.services.tools import all_tools; print(f'Tools loaded: {len(all_tools)}')"
```

Expected: `Tools loaded: 2`

- [ ] **Step 4: Commit**

```bash
git add server/ai/services/tools/
git commit -m "feat(agent): add web_search tool"
```

---

## Task 3：语法检查工具 `grammar_check`

**Files:**
- Create: `server/ai/services/tools/grammar.py`
- Modify: `server/ai/services/tools/__init__.py`

- [ ] **Step 1: 创建语法检查工具文件**

创建 `server/ai/services/tools/grammar.py`：

```python
import json
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from ai.services.llm import create_deepseek

# 语法检查专用 prompt
GRAMMAR_PROMPT = """你是一个英语语法检查专家。请检查以下英文句子的语法错误。

要求：
1. 如果没有错误，返回 {"has_error": false, "corrections": [], "overall_comment": "语法正确"}
2. 如果有错误，返回 JSON 格式：
   {
     "has_error": true,
     "corrections": [
       {"original": "错误部分", "corrected": "修正后", "reason": "用中文解释为什么错"}
     ],
     "overall_comment": "用中文总结主要问题"
   }

只返回 JSON，不要其他文字。"""


@tool
async def grammar_check(text: str) -> str:
    """检查英语句子的语法错误，给出修正建议和错误原因解释。
    当用户输入英文句子要求检查、或用户在练习写作时使用此工具。
    不要用于查词或搜索信息。"""
    if len(text) > 500:
        return json.dumps({"error": "输入过长，请限制在 500 字符以内"}, ensure_ascii=False)

    try:
        model = create_deepseek()
        messages = [
            HumanMessage(content=f"{GRAMMAR_PROMPT}\n\n待检查句子：{text}")
        ]
        response = await model.ainvoke(messages)
        return response.content
    except Exception as e:
        return json.dumps({"error": f"语法检查失败: {e}"}, ensure_ascii=False)
```

- [ ] **Step 2: 更新工具导出**

修改 `server/ai/services/tools/__init__.py`：

```python
from .word import word_lookup
from .search import web_search
from .grammar import grammar_check

all_tools = [word_lookup, web_search, grammar_check]
```

- [ ] **Step 3: 验证导入**

```bash
cd server && uv run python -c "from ai.services.tools import all_tools; print(f'Tools loaded: {len(all_tools)}')"
```

Expected: `Tools loaded: 3`

- [ ] **Step 4: Commit**

```bash
git add server/ai/services/tools/
git commit -m "feat(agent): add grammar_check tool"
```

---

## Task 4：学习进度查询工具 `progress_query`

**Files:**
- Create: `server/ai/services/tools/progress.py`
- Modify: `server/ai/services/tools/__init__.py`

- [ ] **Step 1: 创建进度查询工具文件**

创建 `server/ai/services/tools/progress.py`：

```python
import json
from langchain_core.tools import tool
from sqlalchemy import select, func
from app.database import async_session
from app.models.user import User
from app.models.word_book import WordBookRecord, WordBook
from app.models.course import Course, CourseRecord


@tool
async def progress_query(user_id: str) -> str:
    """查询用户的学习进度数据，包括已掌握单词数、课程完成情况、学习记录。
    当用户询问自己的学习进度、掌握了哪些单词、学了多少课程时使用。"""
    async with async_session() as session:
        # 查询用户基本信息
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return json.dumps({"error": "用户不存在"}, ensure_ascii=False)

        # 查询已掌握单词数
        word_count_result = await session.execute(
            select(func.count(WordBookRecord.id))
            .where(WordBookRecord.user_id == user_id)
            .where(WordBookRecord.is_master == True)
        )
        word_count = word_count_result.scalar() or 0

        # 查询最近掌握的单词（最多 10 个）
        recent_words_result = await session.execute(
            select(WordBook.word)
            .join(WordBookRecord, WordBookRecord.word_id == WordBook.id)
            .where(WordBookRecord.user_id == user_id)
            .where(WordBookRecord.is_master == True)
            .order_by(WordBookRecord.created_at.desc())
            .limit(10)
        )
        recent_words = [row[0] for row in recent_words_result.all()]

        # 查询课程进度
        course_result = await session.execute(
            select(Course.name, CourseRecord.is_purchased)
            .join(CourseRecord, CourseRecord.course_id == Course.id)
            .where(CourseRecord.user_id == user_id)
        )
        courses = [
            {"name": row[0], "purchased": row[1]}
            for row in course_result.all()
        ]

        return json.dumps({
            "word_count": word_count,
            "recent_words": recent_words,
            "courses": courses,
            "day_number": user.day_number or 0,
        }, ensure_ascii=False)
```

- [ ] **Step 2: 更新工具导出（最终版本）**

修改 `server/ai/services/tools/__init__.py`：

```python
from .word import word_lookup
from .search import web_search
from .grammar import grammar_check
from .progress import progress_query

all_tools = [word_lookup, web_search, grammar_check, progress_query]
```

- [ ] **Step 3: 验证导入**

```bash
cd server && uv run python -c "from ai.services.tools import all_tools; print(f'Tools loaded: {len(all_tools)}')"
```

Expected: `Tools loaded: 4`

- [ ] **Step 4: Commit**

```bash
git add server/ai/services/tools/
git commit -m "feat(agent): add progress_query tool"
```

---

## Task 5：集成工具到 Agent + SSE 扩展

**Files:**
- Modify: `server/ai/services/chat.py`
- Modify: `server/ai/services/prompt.py`

- [ ] **Step 1: 修改 `prompt.py` — 更新 normal 角色的 system prompt**

修改 `server/ai/services/prompt.py` 中 `CHAT_MODES` 列表的第一个元素：

```python
{
    "role": "normal",
    "prompt": """你是一个专业的英语学习助手。你可以：
1. 查询单词的释义、音标、例句（使用 word_lookup 工具）
2. 检查英语句子的语法错误（使用 grammar_check 工具）
3. 搜索互联网获取最新信息（使用 web_search 工具）
4. 查询用户的学习进度（使用 progress_query 工具）

当用户的问题可以通过工具获得准确信息时，优先使用工具而不是凭记忆回答。
例如用户问单词意思时，用 word_lookup 查询而不是直接回答。

请用中文回复，专业术语可中英对照。""",
    "label": "💬 智能助手",
    "id": "1",
},
```

> 其他 4 个角色（master、business、qilinge、xiaoman）保持不变。

- [ ] **Step 2: 修改 `chat.py` — 导入工具并传入 Agent**

在 `server/ai/services/chat.py` 顶部添加导入：

```python
import uuid
from ai.services.tools import all_tools
```

修改 `stream_chat()` 函数中的 agent 创建部分（约第 69-73 行）：

将：
```python
agent = create_react_agent(
    model=model,
    tools=[],
    checkpointer=checkpointer,
)
```

改为：
```python
# normal 角色使用工具，其他角色保持空工具
tools = all_tools if role == "normal" else []
agent = create_react_agent(
    model=model,
    tools=tools,
    checkpointer=checkpointer,
)
```

- [ ] **Step 3: 修改 `chat.py` — SSE 事件循环增加工具事件**

修改 `stream_chat()` 中的 `async for event in agent.astream_events(...)` 循环（约第 78-96 行）。

将：
```python
async for event in agent.astream_events(
    {"messages": messages},
    config={"configurable": {"thread_id": thread_id}},
    version="v2",
):
    kind = event.get("event")
    if kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        if chunk:
            # 深度思考内容
            reasoning = getattr(chunk, "additional_kwargs", {}).get(
                "reasoning_content", ""
            )
            if reasoning:
                yield f"data: {json.dumps({'content': reasoning, 'role': 'ai', 'type': 'reasoning'}, ensure_ascii=False)}\n\n"
            # 普通内容
            content_text = chunk.content if hasattr(chunk, "content") else ""
            if content_text:
                yield f"data: {json.dumps({'content': content_text, 'role': 'ai', 'type': 'chat'}, ensure_ascii=False)}\n\n"
```

改为：
```python
async for event in agent.astream_events(
    {"messages": messages},
    config={"configurable": {"thread_id": thread_id}},
    version="v2",
):
    kind = event.get("event")
    # 工具调用开始
    if kind == "on_tool_start":
        tool_name = event.get("name", "")
        tool_input = event.get("data", {}).get("input", "")
        # input 可能是 dict（工具参数）或 str，统一转为 str
        if isinstance(tool_input, dict):
            tool_input = json.dumps(tool_input, ensure_ascii=False)
        call_id = str(uuid.uuid4())[:8]
        yield f"data: {json.dumps({'type': 'tool', 'id': call_id, 'tool': tool_name, 'input': str(tool_input)}, ensure_ascii=False)}\n\n"
    # 工具调用结束
    elif kind == "on_tool_end":
        tool_name = event.get("name", "")
        tool_output = event.get("data", {}).get("output", "")
        yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'output': str(tool_output)}, ensure_ascii=False)}\n\n"
    # 模型流式输出
    elif kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        if chunk:
            # 深度思考内容
            reasoning = getattr(chunk, "additional_kwargs", {}).get(
                "reasoning_content", ""
            )
            if reasoning:
                yield f"data: {json.dumps({'content': reasoning, 'role': 'ai', 'type': 'reasoning'}, ensure_ascii=False)}\n\n"
            # 普通内容
            content_text = chunk.content if hasattr(chunk, "content") else ""
            if content_text:
                yield f"data: {json.dumps({'content': content_text, 'role': 'ai', 'type': 'chat'}, ensure_ascii=False)}\n\n"
```

- [ ] **Step 4: 验证后端代码无语法错误**

```bash
cd server && uv run python -c "from ai.services.chat import stream_chat; print('chat service OK')"
```

Expected: `chat service OK`

- [ ] **Step 5: 启动 AI 服务验证**

```bash
cd server && uv run python -m uvicorn ai.main:ai_app --port 3001 --reload
```

验证：访问 `http://localhost:3001/` 应返回健康检查响应。

- [ ] **Step 6: Commit**

```bash
git add server/ai/services/chat.py server/ai/services/prompt.py
git commit -m "feat(agent): integrate tools into ReAct agent and extend SSE protocol"
```

> **注意：** 如果 `on_tool_start` / `on_tool_end` 事件未触发（DeepSeek 对 tool calling 的支持可能不稳定），需要降级方案：在 `stream_chat()` 的 `web_search` 手动注入逻辑基础上，将其他工具也改为手动调用 + prompt 注入的方式。但这会失去 Agent 自主决策调用工具的能力。建议先测试 `astream_events` 是否正常触发工具事件，再决定是否需要降级。

---

## Task 6：前端类型扩展

**Files:**
- Modify: `packages/common/chat/index.ts`

- [ ] **Step 1: 扩展 ChatMessageType 和 ChatMessage**

修改 `packages/common/chat/index.ts`：

```typescript
export type ChatRole = 'human' | 'ai';
export type ChatRoleType = 'normal' | 'master' | 'business' | 'qilinge' | 'xiaoman';
export type ChatMessageType = 'reasoning' | 'chat' | 'tool' | 'tool_result';
export type ChatMessage = {
    role:ChatRole
    content:string;
    reasoning?:string;
    type:ChatMessageType
    toolId?:string        // 工具调用唯一 ID
    toolName?:string      // 工具名称
    toolInput?:string     // 工具输入
    toolOutput?:string    // 工具输出
}
export type ChatMessageList = ChatMessage[]

export type ChatMode = {
    label:string;
    id:string;
    role:ChatRoleType;
}
export type ChatModeList = ChatMode[]

export type ChatDto = {
    deepThink:boolean;
    webSearch:boolean;
    role:ChatRoleType;
    content:string;
    userId:string;
}

//会话隔离 线程id userId-role  userId:123 role:normal 线程id:123-normal
//查询历史记录 线程id查询 123-normal 查询出123-normal的记录
```

- [ ] **Step 2: 验证类型编译**

```bash
cd apps/web && pnpm type-check
```

Expected: 无类型错误（可能有其他无关警告，忽略即可）

- [ ] **Step 3: Commit**

```bash
git add packages/common/chat/index.ts
git commit -m "feat(agent): extend chat types for tool events"
```

---

## Task 7：前端消息处理

**Files:**
- Modify: `apps/web/src/views/Chat/index.vue`

- [ ] **Step 1: 修改 sendMessage 增加工具事件处理**

修改 `apps/web/src/views/Chat/index.vue` 中的 `sendMessage` 函数（第 24-36 行）：

```typescript
const sendMessage = (message: string, deepThink: boolean, webSearch: boolean) => {
    list.value.push({role: 'human', content: message, type: 'chat'})
    list.value.push({role: 'ai', content: '',reasoning:'' ,type: 'chat'})
    sse<ChatMessage, ChatDto>(CHAT_URL, "POST", {role: role.value, content: message, userId: userId!,deepThink,webSearch
    }, (data) => {
        if(data.type === 'reasoning'){
            list.value[list.value.length - 1].reasoning += data.content
        }
        if(data.type === 'chat'){
            list.value[list.value.length - 1].content += data.content
        }
        // 工具调用开始
        if(data.type === 'tool'){
            list.value.push({
                role: 'ai',
                content: '',
                type: 'tool',
                toolId: data.toolId,
                toolName: data.toolName,
                toolInput: data.toolInput,
            })
        }
        // 工具调用结束 — 更新对应工具消息的结果
        if(data.type === 'tool_result'){
            const lastTool = [...list.value].reverse().find(
                m => m.type === 'tool' && m.toolName === data.toolName
            )
            if(lastTool){
                lastTool.toolOutput = data.toolOutput
            }
        }
    })
}
```

- [ ] **Step 2: 验证前端编译**

```bash
cd apps/web && pnpm type-check
```

Expected: 无类型错误

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/views/Chat/index.vue
git commit -m "feat(agent): handle tool/tool_result SSE events in chat"
```

---

## Task 8：前端工具气泡样式

**Files:**
- Modify: `apps/web/src/views/Chat/components/Bubble.vue`

- [ ] **Step 1: 在模板中添加工具调用和结果的展示**

修改 `apps/web/src/views/Chat/components/Bubble.vue` 的模板部分。

在现有的 `<div v-for="(item, index) in list" :key="index">` 内部，在 `v-else` 块的 `<div>` 之前，添加工具消息的渲染：

将：
```html
<div v-for="(item, index) in list" :key="index">
    <div class="flex justify-end items-center  gap-4 mt-5 mb-5 mr-5" v-if="item.role === 'human'">
        ...
    </div>
    <div class="flex justify-start items-center gap-4 mt-5 mb-5" v-else>
        ...
    </div>
</div>
```

改为：
```html
<div v-for="(item, index) in list" :key="index">
    <!-- 用户消息 -->
    <div class="flex justify-end items-center  gap-4 mt-5 mb-5 mr-5" v-if="item.role === 'human'">
        <div class="text-sm text-white max-w-[80%] rounded-lg p-2 bg-blue-500 shadow-md">
            {{ item.content }}
        </div>
        <div>
            <el-avatar :size="35">user</el-avatar>
        </div>
    </div>
    <!-- 工具调用消息 -->
    <div v-else-if="item.type === 'tool'"
        class="flex justify-start items-center gap-4 mt-3 mb-3 ml-14">
        <div class="text-xs text-gray-400 bg-gray-50 rounded-lg px-3 py-2 max-w-[80%]">
            <span class="inline-block animate-spin mr-1">🔍</span>
            <span>正在调用 <strong>{{ item.toolName }}</strong>: {{ item.toolInput }}</span>
            <span v-if="!item.toolOutput" class="ml-2 inline-block animate-pulse">...</span>
        </div>
    </div>
    <!-- 工具结果消息 -->
    <div v-else-if="item.type === 'tool_result'"
        class="flex justify-start items-center gap-4 mt-1 mb-3 ml-14">
        <div class="text-xs text-green-600 bg-green-50 rounded-lg px-3 py-2 max-w-[80%]">
            ✅ 查询完成
            <details class="mt-1">
                <summary class="cursor-pointer text-gray-500 hover:text-gray-700">查看详情</summary>
                <pre class="mt-1 text-[11px] text-gray-500 whitespace-pre-wrap break-all">{{ item.toolOutput }}</pre>
            </details>
        </div>
    </div>
    <!-- AI 普通/推理消息 -->
    <div class="flex justify-start items-center gap-4 mt-5 mb-5" v-else>
        <div> <el-avatar :size="35">AI</el-avatar></div>
        <div>
            <div v-if="item.role === 'ai' && item.reasoning" class="text-[12px] text-gray-500 max-w-[80%] p-2">
                {{ item.reasoning }}
            </div>
            <div v-if="item.role === 'ai' && item.content !== ''"
                class="text-sm text-gray-700 max-w-[80%] bg-white rounded-lg mt-2 deepseek-markdown"
                v-html="parseMarkdown(item.content)" />
        </div>
    </div>
</div>
```

- [ ] **Step 2: 验证前端编译**

```bash
cd apps/web && pnpm type-check
```

Expected: 无类型错误

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/views/Chat/components/Bubble.vue
git commit -m "feat(agent): add tool call/result bubble styles"
```

---

## Task 9：端到端验证

- [ ] **Step 1: 启动所有服务**

```bash
# 终端 1：启动 AI 服务
cd server && uv run python -m uvicorn ai.main:ai_app --port 3001 --reload

# 终端 2：启动前端
pnpm web
```

- [ ] **Step 2: 测试查词工具**

在前端 Chat 页面选择"智能助手"模式，输入：

```
apple 是什么意思？
```

Expected：
- 出现工具调用气泡：`🔍 正在调用 word_lookup: apple`
- 出现工具结果气泡：`✅ 查询完成`（可展开查看详情）
- AI 回答包含 apple 的音标、释义

- [ ] **Step 3: 测试语法检查工具**

输入：

```
请检查这句话的语法：I goes to school yesterday.
```

Expected：
- 出现工具调用气泡：`🔍 正在调用 grammar_check: I goes to school yesterday.`
- AI 回答指出 "goes" 应为 "went"（过去时），并解释原因

- [ ] **Step 4: 测试学习进度工具**

输入：

```
我学了多少单词？
```

Expected：
- 出现工具调用气泡：`🔍 正在调用 progress_query: {user_id}`
- AI 回答包含已掌握单词数

- [ ] **Step 5: 测试其他角色不受影响**

切换到"英语大师"模式，输入任意问题。Expected：无工具调用气泡，正常聊天回复。

- [ ] **Step 6: Commit 全部改动**

```bash
git add -A
git commit -m "feat: agent tools integration complete"
```

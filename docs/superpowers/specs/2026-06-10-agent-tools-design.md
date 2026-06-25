# Agent 工具化设计文档

> 日期：2026-06-10
> 状态：已批准
> 范围：给现有 Chat 的 `normal` 角色注册 4 个 LangChain Tools

## 背景

项目已有完整的 AI 聊天基础设施：
- DeepSeek LLM 通过 LangChain 集成（`langchain_deepseek.ChatDeepSeek`）
- LangGraph `create_react_agent` 已在使用，但 `tools=[]`（无工具）
- PostgresCheckpointer 实现多轮对话持久化
- SSE 流式输出已打通（`@microsoft/fetch-event-source`）
- 5 个角色人设：normal、master、business、qilinge、xiaoman
- Web 搜索（Bocha API）已集成，但以手动 prompt 注入方式实现

**核心差距**：ReAct Agent 的基础设施已就绪，但没有注册任何工具。本次设计的目标是给 `normal` 角色装上 4 个工具，使其从"对话机器人"进化为能查词、查进度、检查语法、搜索互联网的英语学习 Agent。

## 设计决策

1. **一个 Agent，全部工具** — 不拆分多个角色，由 Agent 根据工具 description 自主决定调用哪个
2. **工具调 service，不直接查表** — 避免 `ai/` 和 `app/` 数据查询逻辑分裂导致页面显示与 Agent 回答不一致
3. **SSE 协议扩展** — 新增 `tool` 和 `tool_result` 事件类型，前端展示工具调用过程
4. **工具描述即控制** — 通过精准的 description 引导 LLM 何时调用哪个工具
5. **只改 normal 角色** — 其他 4 个角色保持 `tools=[]` 不变

## 工具设计

### Tool 1：查词工具 `word_lookup`

**功能**：查询词书数据库，返回单词的音标、释义、例句、是否已掌握

**实现文件**：`server/ai/services/tools/word.py`

**LangChain 定义**：
```python
from langchain_core.tools import tool

@tool
def word_lookup(word: str) -> str:
    """查询英语单词的详细信息，包括音标、中文释义、例句。
    当用户询问某个单词的意思、用法、拼写时使用此工具。
    不要用于检查语法或搜索互联网信息。"""
    # 调用 shared 层的词书查询逻辑
    ...
```

**数据来源**：通过 `server/shared/query/word.py` 的共享函数查询 WordBook 表（共享 PostgreSQL）。不直接写 SQL，确保与 `app/` 层数据一致。

**输入**：`word: str` — 用户查询的单词

**输出**：JSON 字符串，包含 `word`, `phonetic`, `definition`, `example`, `is_mastered`

### Tool 2：语法检查工具 `grammar_check`

**功能**：检查用户输入的英文句子语法错误，给出修正和解释

**实现文件**：`server/ai/services/tools/grammar.py`

**实现方式**：在工具函数内部直接调用 DeepSeek LLM（通过 `create_deepseek()` 创建一个独立的模型实例，不经过 Agent，避免递归调用）。理由：
- 英语学习平台的核心价值是教用户**为什么错**，这需要 LLM 的解释能力
- `language_tool_python` 只能标注错误，不能解释原因
- 通过 prompt 约束输出格式，相同句子可做短期缓存控制成本

**LangChain 定义**：
```python
@tool
def grammar_check(text: str) -> str:
    """检查英语句子的语法错误，给出修正建议和错误原因解释。
    当用户输入英文句子要求检查、或用户在练习写作时使用此工具。
    不要用于查词或搜索信息。"""
    # 调用 DeepSeek 进行语法检查
    ...
```

**输出格式**：
```json
{
  "has_error": true,
  "corrections": [
    {"original": "I goes", "corrected": "I go", "reason": "主语是第一人称 I，谓语动词用原形 go，不用第三人称单数 goes"}
  ],
  "overall_comment": "句子主要问题是主谓一致..."
}
```

### Tool 3：Web 搜索工具 `web_search`

**功能**：封装现有 Bocha API，从手动 prompt 注入改为 LangChain Tool

**实现文件**：`server/ai/services/tools/search.py`

**LangChain 定义**：
```python
@tool
def web_search(query: str) -> str:
    """搜索互联网获取实时信息。仅在以下情况使用：
    1. 用户明确要求搜索
    2. 问题需要最新信息（如新闻、最新术语）
    3. 问题超出英语学习范畴
    查词、语法问题请优先使用 word_lookup 和 grammar_check。"""
    # 调用现有 Bocha API
    ...
```

**关键**：description 中明确列出优先级，避免 LLM 滥用搜索（"hello 是什么意思"不应触发搜索）。

**复用**：现有 `server/ai/services/chat.py` 中的 `bocha_search()` 函数逻辑迁移到此工具中。

### Tool 4：用户学习数据查询 `progress_query`

**功能**：查询用户的学习进度

**实现文件**：`server/ai/services/tools/progress.py`

**LangChain 定义**：
```python
@tool
def progress_query(user_id: int) -> str:
    """查询用户的学习进度数据，包括已掌握单词数、课程完成情况、学习记录。
    当用户询问自己的学习进度、掌握了哪些单词、学了多少课程时使用。"""
    # 调用 shared 层的进度查询逻辑
    ...
```

**数据来源**：通过 `shared/` 的共享函数查询 User、WordBookRecord、CourseRecord 表。**不直接写 SQL**，与 `app/services/` 保持逻辑一致。

**输出**：
```json
{
  "word_count": 128,
  "mastered_words": ["apple", "banana", ...],
  "course_progress": [
    {"course_name": "基础词汇", "completed": 15, "total": 20}
  ],
  "recent_activity": "今天学习了 12 个单词"
}
```

### 工具列表导出

`server/ai/services/tools/__init__.py`：

```python
from .word import word_lookup
from .grammar import grammar_check
from .search import web_search
from .progress import progress_query

all_tools = [word_lookup, grammar_check, web_search, progress_query]
```

## 后端集成

### 修改 `server/ai/services/chat.py`

现有代码：
```python
agent = create_react_agent(model=model, tools=[], checkpointer=checkpointer)
```

改为：
```python
from ai.services.tools import all_tools

# normal 角色使用工具，其他角色保持空工具
tools = all_tools if role == "normal" else []
agent = create_react_agent(model=model, tools=tools, checkpointer=checkpointer)
```

### 修改 `server/ai/services/prompt.py`

给 `normal` 角色的 system prompt 增加工具使用指引：

```python
CHAT_MODES = {
    "normal": {
        "id": 1,
        "label": "智能助手",
        "role": "normal",
        "prompt": """你是一个专业的英语学习助手。你可以：
1. 查询单词的释义、音标、例句（使用 word_lookup 工具）
2. 检查英语句子的语法错误（使用 grammar_check 工具）
3. 搜索互联网获取最新信息（使用 web_search 工具）
4. 查询用户的学习进度（使用 progress_query 工具）

当用户的问题可以通过工具获得准确信息时，优先使用工具而不是凭记忆回答。
例如用户问单词意思时，用 word_lookup 查询而不是直接回答。

请用中文回复，专业术语可中英对照。"""
    },
    # ... 其他角色不变
}
```

### 修改 `server/ai/routers/chat.py`

SSE 输出增加 tool/tool_result 事件：

```python
import uuid

async for event in agent.astream_events(...):
    if event["event"] == "on_tool_start":
        call_id = str(uuid.uuid4())[:8]
        yield f"data: {json.dumps({'type': 'tool', 'id': call_id, 'tool': event['name'], 'input': str(event['data'].get('input', ''))})}\n\n"
    elif event["event"] == "on_tool_end":
        yield f"data: {json.dumps({'type': 'tool_result', 'id': call_id, 'tool': event['name'], 'output': str(event['data'].get('output', ''))})}\n\n"
    elif event["event"] == "on_chat_model_stream":
        # 现有的 reasoning 和 chat 逻辑
        ...
```

## 前端改动

### 类型扩展 `packages/common/chat/index.ts`

```typescript
export type ChatMessageType = 'reasoning' | 'chat' | 'tool' | 'tool_result'

export interface ChatMessage {
  role: ChatRole
  content: string
  reasoning?: string
  type: ChatMessageType
  toolId?: string        // 工具调用唯一 ID，用于匹配 tool 和 tool_result
  toolName?: string      // 工具名称
  toolInput?: string     // 工具输入
  toolOutput?: string    // 工具输出
}
```

### 消息处理 `apps/web/src/views/Chat/index.vue`

`sendMessage` 中增加对新事件类型的处理：

```typescript
if (data.type === 'tool') {
  list.value.push({
    role: 'ai',
    content: '',
    type: 'tool',
    toolName: data.tool,
    toolInput: data.input
  })
}
if (data.type === 'tool_result') {
  // 找到最后一条 tool 消息，更新其结果
  const lastTool = [...list.value].reverse().find(m => m.type === 'tool')
  if (lastTool) {
    lastTool.toolOutput = data.output
  }
}
```

### 气泡样式 `apps/web/src/views/Chat/components/Bubble.vue`

新增工具调用和结果的展示样式：

```
工具调用气泡：
┌──────────────────────────────┐
│ 🔍 正在查询单词: apple        │  (带 loading 动画)
└──────────────────────────────┘

工具结果气泡：
┌──────────────────────────────┐
│ ✅ 查询完成                   │  (折叠显示详细结果)
└──────────────────────────────┘
```

工具调用和结果消息使用较浅的背景色、较小的字体，与正式回答区分开。

tool_result 默认折叠显示摘要（如"✅ 查询完成"），点击可展开查看详细结果。答辩时视觉层次更清晰。

## 共享数据访问

`ai/` 和 `app/` 是两个独立 FastAPI 进程，共享同一个 PostgreSQL。为避免查询逻辑分裂：

在 `server/shared/` 目录新增共享查询函数：

```
server/shared/
  query/
    __init__.py
    word.py       # 词书查询（word_lookup 工具 + app 服务共用）
    progress.py   # 学习进度查询（progress_query 工具 + app 服务共用）
```

两个 app 都从 `shared/query/` 导入，确保数据一致性。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| DeepSeek tool calling 不稳定 | Agent 不调用工具或调用错误 | 降级方案：将工具结果通过 prompt 注入（类似现有 web search 做法） |
| grammar_check LLM 成本 | 每次检查消耗 token | 缓存键：`user_id + model_version + text_hash`，5 分钟 TTL；限制输入最长 500 字符 |
| web_search 被滥用 | Bocha API 额度耗尽 | description 中明确优先级；后端每用户每日调用上限（如 20 次/天）；前端不加限制（可绕过） |
| 共享查询函数维护 | `shared/` 目录职责膨胀 | 仅放查询函数，不放业务逻辑；保持轻量 |

## 不在范围内

以下功能本次不实现，留作后续迭代：
- 给其他角色（master/business/qilinge/xiaoman）添加工具
- 代码执行沙箱
- 语音识别/合成
- 长期记忆（向量数据库）
- 自动批改 Agent
- 学习路径推荐 Agent

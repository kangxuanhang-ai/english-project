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
                yield _sse({"content": reasoning, "role": "ai", "type": "reasoning"})
            content_text = chunk.content if hasattr(chunk, "content") else ""
            if isinstance(content_text, list):
                content_text = "".join(
                    b if isinstance(b, str) else str(b.get("text", ""))
                    for b in content_text
                    if isinstance(b, (str, dict))
                )
            if content_text:
                content_text = chat_filter.feed(str(content_text))
                if content_text:
                    yield _sse({"content": content_text, "role": "ai", "type": "chat"})

    yield _sse({"type": "done"})


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

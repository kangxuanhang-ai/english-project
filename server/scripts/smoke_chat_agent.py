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

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from ai.services.agent_factory import get_or_create_agent
from ai.services.chat import get_chat_history, get_checkpointer
from ai.services.llm import get_llm
from ai.services.middleware.chat_prompt import ChatContext
from ai.services.sse_adapter import stream_legacy_sse


async def main() -> int:
    cp = await get_checkpointer()
    model = get_llm(False)
    tid = "smoke-phase1-cross-compat"
    await cp.adelete_thread(tid)

    old = create_react_agent(
        model=model,
        tools=[],
        checkpointer=cp,
        prompt=SystemMessage(content="legacy"),
    )
    await old.ainvoke(
        {"messages": [HumanMessage(content="legacy hello")]},
        config={"configurable": {"thread_id": tid}},
    )

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

    hist = await get_chat_history(tid, limit=50)
    assert len(hist["messages"]) >= 2, hist

    try:
        await cp.adelete_thread(tid)
    except Exception:
        pass
    print("smoke_chat_agent: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

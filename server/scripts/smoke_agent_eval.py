#!/usr/bin/env python3
"""本地快速跑 1 条 agent 评测用例（不上传 experiment）。"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from ai.data.agent_eval_cases import AGENT_EVAL_CASES, case_to_langsmith_example
from ai.services.agent_eval import _score_tool_accuracy, run_eval_case
from ai.services.chat_blocks import has_recommend_json_leak


async def main() -> int:
    case = AGENT_EVAL_CASES[0]
    ex = case_to_langsmith_example(case)
    print(f"case: {case['id']} ({case['category']})")
    print(f"message: {case['message']}")

    out = await run_eval_case(ex["inputs"])
    ref = ex["outputs"]
    tool_score, tool_comment = _score_tool_accuracy(out["tools_called"], ref)
    leak = has_recommend_json_leak(out["response"]) if ref.get("check_json_leak") else False

    print(f"tools_called: {out['tools_called']}")
    print(f"latency_ms: {out['latency_ms']}")
    print(f"tool_accuracy: {tool_score} ({tool_comment})")
    if ref.get("check_json_leak"):
        print(f"json_leak: {leak}")
    print(f"response preview: {out['response'][:200]}...")

    ok = tool_score >= 1.0 and (not ref.get("check_json_leak") or not leak)
    print("smoke_agent_eval: PASS" if ok else "smoke_agent_eval: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

#!/usr/bin/env python3
"""运行 normal 角色 agent LangSmith experiment 评测。"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from langsmith import Client, evaluate

from ai.config import ai_settings
from ai.data.agent_eval_cases import DATASET_NAME
from ai.services.agent_eval import (
    EVALUATORS,
    SUMMARY_EVALUATORS,
    configure_eval_tracing,
    reset_eval_async_resources,
    run_eval_case,
)

logger = logging.getLogger(__name__)

# 全进程复用同一 event loop（LangSmith evaluate 的 sync target 会多次调用）
_EVAL_LOOP: asyncio.AbstractEventLoop | None = None


def _get_eval_loop() -> asyncio.AbstractEventLoop:
    global _EVAL_LOOP
    if _EVAL_LOOP is None or _EVAL_LOOP.is_closed():
        _EVAL_LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_EVAL_LOOP)
    return _EVAL_LOOP


def _sync_target(inputs: dict) -> dict:
    """在固定 event loop 上跑 async agent，避免 asyncpg/httpx 跨 loop 报错。"""
    loop = _get_eval_loop()

    async def _run() -> dict:
        try:
            return await run_eval_case(inputs)
        except Exception:
            await reset_eval_async_resources()
            raise

    return loop.run_until_complete(_run())


def _print_summary(results) -> None:
    if hasattr(results, "experiment_name"):
        print(f"  name: {results.experiment_name}")

    scores: dict[str, list[float]] = {}
    errors = 0
    rows = getattr(results, "results", None) or []
    for row in rows:
        run = getattr(row, "run", None)
        if run and getattr(run, "error", None):
            errors += 1
        eval_block = getattr(row, "evaluation_results", None)
        eval_list = eval_block.get("results", []) if isinstance(eval_block, dict) else []
        for ev in eval_list:
            key = ev.get("key") if isinstance(ev, dict) else getattr(ev, "key", None)
            score = ev.get("score") if isinstance(ev, dict) else getattr(ev, "score", None)
            if key is not None and score is not None:
                scores.setdefault(key, []).append(float(score))

    if errors:
        print(f"  errors: {errors} runs failed (see LangSmith trace)")
    for key, vals in sorted(scores.items()):
        avg = sum(vals) / len(vals) if vals else 0.0
        print(f"  {key}: avg={avg:.2%} ({len(vals)} runs)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run agent eval experiment on LangSmith")
    parser.add_argument(
        "--prefix",
        default="english-agent-normal",
        help="Experiment name prefix (default: english-agent-normal)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only run first N examples (0 = all)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Max concurrent eval runs (default: 1; >1 may break async DB on Windows)",
    )
    args = parser.parse_args()

    if not ai_settings.langchain_api_key.strip():
        print("LANGCHAIN_API_KEY 未配置", file=sys.stderr)
        return 1
    if not ai_settings.deepseek_api_key.strip():
        print("DEEPSEEK_API_KEY 未配置", file=sys.stderr)
        return 1

    configure_eval_tracing()
    client = Client(api_key=ai_settings.langchain_api_key)

    if not client.has_dataset(dataset_name=DATASET_NAME):
        print(
            f"Dataset {DATASET_NAME} 不存在，请先运行: uv run python scripts/create_agent_eval_dataset.py",
            file=sys.stderr,
        )
        return 1

    if args.concurrency > 1:
        print("warning: concurrency>1 在 Windows 上可能触发 async loop 错误，建议使用 --concurrency 1")

    data: str | list = DATASET_NAME
    if args.limit > 0:
        ds = client.read_dataset(dataset_name=DATASET_NAME)
        data = list(client.list_examples(dataset_id=ds.id, limit=args.limit))
        print(f"Running subset: {len(data)} examples")

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    prefix = f"{args.prefix}-{stamp}"

    print(f"Starting experiment {prefix} on dataset {DATASET_NAME} ...")
    print(f"AGENT_EVAL_USER_ID={ai_settings.agent_eval_user_id!r} (推荐设为数据库里真实用户 ID)")

    loop = _get_eval_loop()
    try:
        results = evaluate(
            _sync_target,
            data=data,
            evaluators=EVALUATORS,
            summary_evaluators=SUMMARY_EVALUATORS,
            experiment_prefix=prefix,
            description="Phase 3 normal-role agent regression eval",
            max_concurrency=max(1, args.concurrency),
            client=client,
            metadata={"role": "normal", "source": "run_agent_eval"},
        )
    finally:
        loop.run_until_complete(reset_eval_async_resources())
        loop.close()

    print("Experiment finished.")
    _print_summary(results)
    print(f"View in LangSmith → Datasets & Experiments → {DATASET_NAME}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())

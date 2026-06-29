#!/usr/bin/env python3
"""创建 / 同步 LangSmith 评测 dataset（english-agent-normal-v1）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langsmith import Client

from ai.config import ai_settings
from ai.data.agent_eval_cases import AGENT_EVAL_CASES, DATASET_NAME, case_to_langsmith_example


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or refresh agent eval dataset on LangSmith")
    parser.add_argument("--force", action="store_true", help="Delete and recreate dataset")
    args = parser.parse_args()

    if not ai_settings.langchain_api_key.strip():
        print("LANGCHAIN_API_KEY 未配置", file=sys.stderr)
        return 1

    client = Client(api_key=ai_settings.langchain_api_key)
    examples = [case_to_langsmith_example(c) for c in AGENT_EVAL_CASES]

    if client.has_dataset(dataset_name=DATASET_NAME):
        if args.force:
            client.delete_dataset(dataset_name=DATASET_NAME)
            print(f"deleted dataset {DATASET_NAME}")
        else:
            ds = client.read_dataset(dataset_name=DATASET_NAME)
            existing = list(client.list_examples(dataset_id=ds.id, limit=100))
            if len(existing) == len(examples):
                print(f"dataset {DATASET_NAME} already has {len(existing)} examples (use --force to recreate)")
                return 0
            print(f"dataset exists with {len(existing)} examples, expected {len(examples)} — recreating")
            client.delete_dataset(dataset_name=DATASET_NAME)

    client.create_dataset(
        DATASET_NAME,
        description="English learning normal-role agent regression eval (Phase 3)",
    )
    client.create_examples(dataset_name=DATASET_NAME, examples=examples)
    print(f"created {DATASET_NAME} with {len(examples)} examples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

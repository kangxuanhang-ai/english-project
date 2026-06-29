#!/usr/bin/env python3
"""将 prompt.py 中 6 个角色的 system prompt 推送到 LangSmith Hub。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client
from langsmith.utils import LangSmithConflictError

from ai.config import ai_settings
from ai.services.prompt import CHAT_MODES
from ai.services.prompt_loader import hub_prompt_id


def main() -> int:
    if not ai_settings.langchain_api_key.strip():
        print("LANGCHAIN_API_KEY 未配置，无法推送", file=sys.stderr)
        return 1

    client = Client(api_key=ai_settings.langchain_api_key)
    for mode in CHAT_MODES:
        role = mode["role"]
        identifier = hub_prompt_id(role)
        tmpl = ChatPromptTemplate.from_messages([("system", mode["prompt"])])
        try:
            url = client.push_prompt(
                identifier,
                object=tmpl,
                description=f"English learning chat — role={role}",
            )
            print(f"pushed {identifier}: {url}")
        except LangSmithConflictError:
            # Hub 内容与本地一致，无需新 commit（409）
            print(f"skip {identifier}: unchanged")
    print("push_prompts_to_hub: done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

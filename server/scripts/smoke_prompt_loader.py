#!/usr/bin/env python3
"""Phase 2: LangSmith Hub prompt 拉取与本地 fallback 冒烟。"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.services.prompt import CHAT_MODES, get_local_role_prompt
from ai.services.prompt_loader import get_role_base_prompt, hub_prompt_id


async def main() -> int:
    failed = 0
    for mode in CHAT_MODES:
        role = mode["role"]
        hub = await get_role_base_prompt(role)
        local = get_local_role_prompt(role)
        if hub == local:
            print(f"OK  {hub_prompt_id(role)}  ({len(hub)} chars)")
        else:
            print(f"FAIL {hub_prompt_id(role)}  hub={len(hub)} local={len(local)}")
            failed += 1

    if failed:
        print(f"smoke_prompt_loader: FAIL ({failed} mismatches)")
        return 1
    print("smoke_prompt_loader: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""AI 包初始化：Windows 上 psycopg/LangGraph 需要 SelectorEventLoop，须在 uvicorn 建 loop 之前设置。"""
from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

"""Windows-safe uvicorn 入口。

Python 3.14 + Windows 默认 ProactorEventLoop 与 psycopg(LangGraph checkpointer) 不兼容，
须显式指定 SelectorEventLoop（见 uvicorn.loops.asyncio 在 win32 非 subprocess 时用 Proactor）。
"""
from __future__ import annotations

import sys

import uvicorn

_WIN_LOOP = "asyncio:SelectorEventLoop"


def main() -> None:
    loop = _WIN_LOOP if sys.platform == "win32" else "auto"
    uvicorn.run(
        "ai.main:ai_app",
        host="0.0.0.0",
        port=3001,
        reload=True,
        loop=loop,
    )


if __name__ == "__main__":
    main()

"""进程内短 TTL 缓存 list_tools 结果。"""
from __future__ import annotations

import time
from typing import Any

_TTL = 300
_MAX_ENTRIES = 512
_store: dict[tuple, tuple[float, Any]] = {}


def _cleanup_expired() -> None:
    now = time.time()
    expired = [k for k, (exp, _) in _store.items() if exp <= now]
    for k in expired:
        _store.pop(k, None)


def get_cached(key: tuple) -> Any | None:
    item = _store.get(key)
    if not item:
        return None
    expires, value = item
    if time.time() > expires:
        _store.pop(key, None)
        return None
    return value


def set_cached(key: tuple, value: Any) -> None:
    _cleanup_expired()
    if len(_store) >= _MAX_ENTRIES:
        oldest = min(_store.items(), key=lambda kv: kv[1][0])[0]
        _store.pop(oldest, None)
    _store[key] = (time.time() + _TTL, value)

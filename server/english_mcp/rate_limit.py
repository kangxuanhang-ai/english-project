import time

MAX_GRAMMAR_PER_MINUTE = 15
_hits: dict[str, list[float]] = {}


def allow_grammar(key: str) -> bool:
    now = time.time()
    hits = [t for t in _hits.get(key, []) if now - t < 60]
    if len(hits) >= MAX_GRAMMAR_PER_MINUTE:
        return False
    hits.append(now)
    _hits[key] = hits
    return True

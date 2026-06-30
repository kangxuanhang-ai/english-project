import time

MAX_GRAMMAR_PER_MINUTE = 15
MAX_GRAMMAR_ANONYMOUS_PER_MINUTE = 3
_hits: dict[str, list[float]] = {}


def allow_grammar(key: str, *, anonymous: bool = False) -> bool:
    limit = MAX_GRAMMAR_ANONYMOUS_PER_MINUTE if anonymous else MAX_GRAMMAR_PER_MINUTE
    now = time.time()
    hits = [t for t in _hits.get(key, []) if now - t < 60]
    if len(hits) >= limit:
        return False
    hits.append(now)
    _hits[key] = hits
    return True

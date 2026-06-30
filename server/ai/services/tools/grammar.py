import time

from langchain_core.tools import tool

from app.services.grammar_check import check_grammar

MAX_GRAMMAR_PER_MINUTE = 15
_grammar_hits: dict[str, list[float]] = {}


def _allow_grammar(user_id: str) -> bool:
    now = time.time()
    hits = [t for t in _grammar_hits.get(user_id, []) if now - t < 60]
    if len(hits) >= MAX_GRAMMAR_PER_MINUTE:
        return False
    hits.append(now)
    _grammar_hits[user_id] = hits
    return True


def make_grammar_check(user_id: str):
    @tool
    async def grammar_check(text: str) -> str:
        """检查英语句子的语法错误，给出修正建议和错误原因解释。
        当用户输入英文句子要求检查、或用户在练习写作时使用此工具。
        不要用于查词或搜索信息。"""
        if not _allow_grammar(user_id):
            return "语法检查请求过于频繁，请稍后再试。"

        return await check_grammar(text)

    return grammar_check

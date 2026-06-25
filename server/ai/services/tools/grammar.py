import time

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from ai.services.llm import get_llm

GRAMMAR_PROMPT = """你是一个英语语法检查专家。请检查以下英文句子的语法错误。

输出格式要求（严格遵守，每行一个字段，不要 JSON）：
- 如果没有错误，只输出一行：语法正确
- 如果有错误，按以下格式输出（共 4 行，解释限一句话）：
语法错误：[用一句话概括错误类型，如「主谓不一致」]
原句：[原始句子]
修正：[修正后的句子]
说明：[一句话解释原因，不要重复啰嗦]

只输出上述内容，不要加前缀、markdown 或额外段落。"""

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

        if len(text) > 500:
            return "输入过长，请限制在 500 字符以内。"

        try:
            model = get_llm()
            messages = [
                HumanMessage(content=f"{GRAMMAR_PROMPT}\n\n待检查句子：{text}")
            ]
            response = await model.ainvoke(messages)
            return response.content
        except Exception as e:
            return f"语法检查失败：{e}"

    return grammar_check

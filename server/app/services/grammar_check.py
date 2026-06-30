from langchain_core.messages import HumanMessage

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

MAX_GRAMMAR_TEXT_LEN = 500


async def check_grammar(text: str) -> str:
    """检查英文句子语法，返回纯文本报告（不含鉴权与限流）。"""
    if len(text) > MAX_GRAMMAR_TEXT_LEN:
        return "输入过长，请限制在 500 字符以内。"

    try:
        model = get_llm()
        messages = [HumanMessage(content=f"{GRAMMAR_PROMPT}\n\n待检查句子：{text}")]
        response = await model.ainvoke(messages)
        return response.content
    except Exception as e:
        return f"语法检查失败：{e}"

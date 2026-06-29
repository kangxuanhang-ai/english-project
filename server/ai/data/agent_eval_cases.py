"""normal 角色 agent 回归评测用例（Phase 3）。"""
from __future__ import annotations

from typing import Any, TypedDict


class EvalCase(TypedDict, total=False):
    id: str
    category: str
    message: str
    web_search: bool
    disable_auto_web_search: bool
    expected_tools: list[str]
    forbidden_tools: list[str]
    check_json_leak: bool
    max_latency_ms: int


def _case(
    id: str,
    category: str,
    message: str,
    *,
    web_search: bool = False,
    disable_auto_web_search: bool = False,
    expected_tools: list[str] | None = None,
    forbidden_tools: list[str] | None = None,
    check_json_leak: bool = False,
    max_latency_ms: int = 45000,
) -> EvalCase:
    return {
        "id": id,
        "category": category,
        "message": message,
        "web_search": web_search,
        "disable_auto_web_search": disable_auto_web_search,
        "expected_tools": expected_tools or [],
        "forbidden_tools": forbidden_tools or [],
        "check_json_leak": check_json_leak,
        "max_latency_ms": max_latency_ms,
    }


AGENT_EVAL_CASES: list[EvalCase] = [
    # 查词
    _case("word-1", "word_lookup", "abandon 什么意思", expected_tools=["word_lookup"]),
    _case("word-2", "word_lookup", "请查询单词 resilient 的含义", expected_tools=["word_lookup"]),
    _case("word-3", "word_lookup", "elephant 这个单词怎么读", expected_tools=["word_lookup"]),
    _case("word-4", "word_lookup", "persistent 和 consistent 有什么区别", expected_tools=["word_lookup"]),
    # 语法
    _case("grammar-1", "grammar_check", "帮我检查这句话：He go to school yesterday", expected_tools=["grammar_check"]),
    _case("grammar-2", "grammar_check", "语法纠错：I have went there yesterday", expected_tools=["grammar_check"]),
    _case("grammar-3", "grammar_check", "She don't like apples 对吗", expected_tools=["grammar_check"]),
    # 推荐
    _case(
        "recommend-1",
        "course_recommendation",
        "推荐一门适合我的英语课程",
        expected_tools=["course_recommendation"],
        check_json_leak=True,
    ),
    _case(
        "recommend-2",
        "course_recommendation",
        "帮我规划一下接下来怎么学英语",
        expected_tools=["course_recommendation"],
    ),
    _case(
        "recommend-3",
        "course_recommendation",
        "再推荐一门别的课试试",
        expected_tools=["course_recommendation"],
        check_json_leak=True,
    ),
    _case(
        "recommend-4",
        "course_recommendation",
        "给我推荐两门课",
        expected_tools=["course_recommendation"],
        check_json_leak=True,
    ),
    # 知识库
    _case("knowledge-1", "knowledge_search", "麒麟哥是谁", expected_tools=["knowledge_search"]),
    _case("knowledge-2", "knowledge_search", "这个平台有哪些功能", expected_tools=["knowledge_search"]),
    _case("knowledge-3", "knowledge_search", "口语考官模式是干什么的", expected_tools=["knowledge_search"]),
    _case("knowledge-4", "knowledge_search", "小满模式是什么", expected_tools=["knowledge_search"]),
    # 购课
    _case("purchase-1", "course_purchase", "帮我买第一个", expected_tools=["course_purchase"]),
    _case("purchase-2", "course_purchase", "购买第二个推荐课", expected_tools=["course_purchase"]),
    # 进度
    _case("progress-1", "progress_query", "我今天学习进度怎么样", expected_tools=["progress_query"]),
    _case("progress-2", "progress_query", "我最近掌握了哪些单词", expected_tools=["progress_query"]),
    # 负例：未开联网时不应走知识库查天气
    _case(
        "negative-weather-1",
        "negative_no_knowledge",
        "今天北京天气怎么样",
        disable_auto_web_search=True,
        forbidden_tools=["knowledge_search"],
    ),
    _case(
        "negative-weather-2",
        "negative_no_knowledge",
        "上海明天会下雨吗",
        disable_auto_web_search=True,
        forbidden_tools=["knowledge_search"],
    ),
    # 生产行为：自动联网时也不应调用 knowledge_search
    _case(
        "negative-weather-auto",
        "negative_no_knowledge",
        "今天保定天气怎么样",
        forbidden_tools=["knowledge_search"],
    ),
    # 防泄漏专项
    _case(
        "no-leak-1",
        "no_json_leak",
        "推荐一门适合初学者的课",
        expected_tools=["course_recommendation"],
        check_json_leak=True,
    ),
]

DATASET_NAME = "english-agent-normal-v1"


def case_to_langsmith_example(case: EvalCase) -> dict[str, Any]:
    """转为 LangSmith dataset example 结构。"""
    return {
        "inputs": {
            "message": case["message"],
            "web_search": case.get("web_search", False),
            "disable_auto_web_search": case.get("disable_auto_web_search", False),
        },
        "outputs": {
            "expected_tools": case.get("expected_tools") or [],
            "forbidden_tools": case.get("forbidden_tools") or [],
            "check_json_leak": case.get("check_json_leak", False),
            "max_latency_ms": case.get("max_latency_ms", 45000),
        },
        "metadata": {
            "case_id": case["id"],
            "category": case["category"],
        },
    }

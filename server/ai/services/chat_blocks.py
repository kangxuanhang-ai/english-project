"""聊天 SSE 与历史还原共用的 block 解析与 JSON 过滤。"""
import json
import re

_JSON_INSTRUCTION_LEAK = re.compile(
    r"请遵循|如下.*JSON|开始处理输入|推荐输出|输入数据后|请返回严格"
)


def _strip_recommend_code_fences(text: str) -> str:
    def repl(m: re.Match) -> str:
        block = m.group(0)
        if _looks_like_recommend_fragment(block) or '"courses"' in block:
            return ""
        return block

    return re.sub(r"```[\w]*\n?[\s\S]*?```", repl, text)


def _is_leaked_recommend_line(line: str) -> bool:
    t = line.strip()
    if not t:
        return False
    if _JSON_INSTRUCTION_LEAK.search(t):
        return True
    if re.match(r'^\s*"[a-z_]+"\s*:?\s*[,{\[]?$', t):
        return True
    if t in ('"courses"', '"courses":', "{"):
        return True
    if re.match(r'^[\[{",}\]]+$', t):
        return True
    if t.startswith("```"):
        return True
    return _looks_like_recommend_fragment(t) and not any("\u4e00" <= c <= "\u9fff" for c in t)


def _looks_like_recommend_fragment(text: str) -> bool:
    keys = (
        '"courses"', '"course_id"', '"match_score"', '"daily_plan"',
        '"new_words_per_day"', '"review_frequency"', '"estimated_completion"',
    )
    return any(k in text for k in keys) or re.search(r'^\s*"courses"\s*$', text, re.M) is not None


def _is_mostly_recommend_json_leak(text: str) -> bool:
    stripped = text.strip()
    if not stripped or not _looks_like_recommend_fragment(stripped):
        return False
    if stripped[0] in "{[,\"":
        return True
    chinese = sum(1 for c in stripped if "\u4e00" <= c <= "\u9fff")
    return chinese / max(len(stripped), 1) < 0.28


def _polish_prose(text: str) -> str:
    """去掉 JSON 键名残留，如 "courses我强烈推荐 → 我强烈推荐"""
    if not text:
        return text
    chinese_idx = next((i for i, c in enumerate(text) if "\u4e00" <= c <= "\u9fff"), -1)
    if chinese_idx > 0:
        prefix = text[:chinese_idx]
        if any(
            k in prefix
            for k in ("courses", "course_id", "match_score", "daily_plan", "summary")
        ) or not prefix.strip(' "\'{[,]}:\t\n\r'):
            text = text[chinese_idx:]
    return text.lstrip(' "\'{[,]}:\t\n\r')


def _extract_natural_language_tail(text: str) -> str:
    last = text.rfind("}")
    if last != -1 and last < len(text) - 1:
        tail = text[last + 1 :].strip()
        if tail and any("\u4e00" <= c <= "\u9fff" for c in tail) and not _looks_like_recommend_fragment(tail):
            return _polish_prose(tail)

    lines = []
    for line in text.split("\n"):
        t = line.strip()
        if not t:
            continue
        if t.startswith('"') and ":" in t[:20]:
            continue
        if t[0] in "{[,":
            continue
        if any("\u4e00" <= c <= "\u9fff" for c in t) and not _looks_like_recommend_fragment(t):
            lines.append(line)
    return _polish_prose("\n".join(lines).strip())


def _find_balanced_json_end(text: str, start: int) -> int:
    if start >= len(text) or text[start] != "{":
        return -1
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _strip_recommend_json_buffer(text: str) -> str:
    """对累积 buffer 做推荐 JSON 过滤（与前端 sanitizeContent 对齐）。"""
    if not text:
        return text

    text = re.sub(r"__RECOMMEND_JSON__[\s\S]*?__END_RECOMMEND_JSON__", "", text)

    if "{" not in text and "[" not in text:
        if _is_mostly_recommend_json_leak(text):
            return _extract_natural_language_tail(text)
        if _looks_like_recommend_fragment(text):
            return _extract_natural_language_tail(text)
        return text

    result = []
    i = 0
    while i < len(text):
        brace = text.find("{", i)
        if brace == -1:
            remainder = text[i:]
            if _is_mostly_recommend_json_leak(remainder) or _looks_like_recommend_fragment(remainder):
                tail = _extract_natural_language_tail(remainder)
                if tail:
                    result.append(tail)
            else:
                result.append(remainder)
            break

        result.append(text[i:brace])
        end = _find_balanced_json_end(text, brace)
        if end == -1:
            tail = text[brace:]
            if not _looks_like_recommend_fragment(tail):
                result.append(tail)
            break

        candidate = text[brace : end + 1]
        try:
            obj = json.loads(candidate)
            is_rec = isinstance(obj.get("courses"), list)
        except json.JSONDecodeError:
            is_rec = _looks_like_recommend_fragment(candidate)

        if is_rec or _looks_like_recommend_fragment(candidate):
            i = end + 1
        else:
            result.append(candidate)
            i = end + 1

    out = _polish_prose("".join(result).strip())
    out = _strip_recommend_code_fences(out)
    out = "\n".join(line for line in out.split("\n") if not _is_leaked_recommend_line(line)).strip()
    if _looks_like_recommend_fragment(out) and _is_mostly_recommend_json_leak(out):
        return _extract_natural_language_tail(out)
    return out


def has_recommend_json_leak(text: str) -> bool:
    """评测用：回复正文是否泄漏推荐 JSON 结构。"""
    if not text:
        return False
    if '{ "courses"' in text or '"courses":' in text:
        return True
    return _looks_like_recommend_fragment(text) and _is_mostly_recommend_json_leak(text)


class ChatContentFilter:
    """流式 chat 内容缓冲过滤，避免 JSON 分 chunk 泄漏。"""

    def __init__(self) -> None:
        self._buf = ""
        self._safe_len = 0

    def feed(self, chunk: str) -> str:
        if not chunk:
            return ""
        self._buf += chunk
        safe = _strip_recommend_json_buffer(self._buf)
        emitted = safe[self._safe_len :]
        self._safe_len = len(safe)
        return emitted


def coerce_tool_output_text(tool_output) -> str:
    """LangGraph on_tool_end 的 output 常为 ToolMessage，str() 是其 repr 而非 content。"""
    if tool_output is None:
        return ""
    if isinstance(tool_output, str):
        return tool_output
    content = getattr(tool_output, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    if isinstance(tool_output, dict):
        if isinstance(tool_output.get("content"), str):
            return tool_output["content"]
        return json.dumps(tool_output, ensure_ascii=False)
    return str(tool_output)


def extract_grammar_block(raw: str) -> dict | None:
    """从 grammar_check 工具输出提取结构化结果。"""
    text = (raw or "").strip()
    if not text:
        return None
    if "语法正确" in text and not re.search(r"语法错误[：:]", text):
        return {"ok": True, "summary": "语法正确，没有发现错误。"}

    def pick(label: str) -> str:
        m = re.search(rf"{re.escape(label)}[：:]\s*(.+)", text)
        return m.group(1).strip() if m else ""

    error = pick("语法错误")
    original = pick("原句")
    corrected = pick("修正")
    explanation = pick("说明") or pick("解释")
    if not error and not original and not corrected:
        return None
    return {
        "ok": False,
        "error": error or None,
        "original": original or None,
        "corrected": corrected or None,
        "explanation": explanation or None,
    }


def extract_recommend_block(raw: str) -> dict | None:
    """从 tool 输出中提取推荐 JSON（兼容纯 JSON 与带标记块）。"""
    if not raw:
        return None

    marker_start = "__RECOMMEND_JSON__"
    marker_end = "__END_RECOMMEND_JSON__"
    if marker_start in raw and marker_end in raw:
        json_part = raw.split(marker_start, 1)[1].split(marker_end, 1)[0].strip()
        block = _parse_recommend_json(json_part)
        if block:
            return block

    block = _parse_recommend_json(raw.strip())
    if block:
        return block

    return _parse_recommend_from_agent_text(raw)


def _parse_purchase_json(raw: str) -> dict | None:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    action = data.get("action")
    if action not in ("confirm", "resume_pay", "already_owned", "not_found"):
        return None
    block = {"action": action, "message": data.get("message")}
    if data.get("selected_index") is not None:
        block["selected_index"] = data["selected_index"]
    if data.get("recommend_titles"):
        block["recommend_titles"] = data["recommend_titles"]
    if data.get("course"):
        block["course"] = data["course"]
    return block


def extract_purchase_block(raw: str) -> dict | None:
    """从 course_purchase 工具输出提取结构化购买块。"""
    if not raw:
        return None

    marker_start = "__PURCHASE_JSON__"
    marker_end = "__END_PURCHASE_JSON__"
    if marker_start in raw and marker_end in raw:
        json_part = raw.split(marker_start, 1)[1].split(marker_end, 1)[0].strip()
        block = _parse_purchase_json(json_part)
        if block:
            return block

    return _parse_purchase_json(raw.strip())


def _parse_recommend_json(raw: str) -> dict | None:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data.get("courses"), list) or not data["courses"]:
        return None
    return {
        "courses": data["courses"],
        "daily_plan": data.get("daily_plan"),
        "summary": data.get("summary"),
    }


def _parse_recommend_from_agent_text(text: str) -> dict | None:
    """从可读推荐文本反解析（旧历史兼容）。"""
    courses = []
    pattern = re.compile(
        r"(\d+)\.\s*《(.+?)》（匹配度\s*(\d+)%）\s*\n\s*理由：(.+?)(?=\n\d+\.\s*《|\n\n|$)",
        re.S,
    )
    for m in pattern.finditer(text):
        courses.append(
            {
                "course_id": None,
                "title": m.group(2).strip(),
                "reason": m.group(4).strip(),
                "match_score": int(m.group(3)) / 100,
            }
        )
    if not courses:
        return None

    daily_plan = {}
    m_words = re.search(r"每天新学\s*(\d+)\s*词", text)
    m_review = re.search(r"，([^，\n]+复习[^，\n]*)", text)
    m_eta = re.search(r"预计完成：(.+)", text)
    if m_words:
        daily_plan["new_words_per_day"] = int(m_words.group(1))
    if m_review:
        daily_plan["review_frequency"] = m_review.group(1).strip()
    if m_eta:
        daily_plan["estimated_completion"] = m_eta.group(1).strip()

    return {"courses": courses, "daily_plan": daily_plan or None, "summary": None}


def _tool_summary(_tool_name: str, content: str) -> str:
    """工具输出首行摘要，供历史气泡展示。"""
    if not content:
        return ""
    line = content.strip().split("\n")[0].strip()
    if len(line) > 120:
        return line[:117] + "..."
    return line


def fold_messages_for_history(messages: list) -> list:
    """将 LangGraph 消息折叠为前端 ChatMessage 结构。"""
    result: list[dict] = []
    pending_intro: str | None = None
    pending_recommend: dict | None = None
    pending_grammar: dict | None = None
    pending_purchase: dict | None = None
    pending_tools: list[dict] = []

    for msg in messages:
        msg_type = getattr(msg, "type", "")

        if msg_type == "human":
            pending_intro = None
            pending_recommend = None
            pending_grammar = None
            pending_purchase = None
            pending_tools = []
            result.append(
                {
                    "role": "human",
                    "content": msg.content or "",
                    "type": "chat",
                }
            )
            continue

        if msg_type == "tool":
            tool_name = getattr(msg, "name", "") or ""
            if tool_name == "course_recommendation":
                pending_recommend = extract_recommend_block(msg.content or "")
            elif tool_name == "grammar_check":
                pending_grammar = extract_grammar_block(msg.content or "")
            elif tool_name == "course_purchase":
                pending_purchase = extract_purchase_block(msg.content or "")
            else:
                pending_tools.append(
                    {
                        "name": tool_name,
                        "summary": _tool_summary(tool_name, msg.content or ""),
                    }
                )
            continue

        if msg_type != "ai":
            continue

        if getattr(msg, "tool_calls", None):
            if msg.content:
                pending_intro = msg.content
            continue

        reasoning = getattr(msg, "additional_kwargs", {}).get("reasoning_content")
        final_content = msg.content or ""

        item: dict = {
            "role": "ai",
            "type": "chat",
            "reasoning": reasoning,
        }

        if pending_recommend:
            item["recommendBlock"] = pending_recommend
            item["content"] = pending_intro or ""
            if final_content and final_content != (pending_intro or ""):
                item["contentAfter"] = final_content
            elif final_content and not pending_intro:
                item["contentAfter"] = final_content
            pending_intro = None
            pending_recommend = None
        elif pending_purchase:
            item["purchaseBlock"] = pending_purchase
            item["content"] = pending_intro or ""
            if final_content and final_content != (pending_intro or ""):
                item["contentAfter"] = final_content
            elif final_content and not pending_intro:
                item["contentAfter"] = final_content
            pending_intro = None
            pending_purchase = None
        elif pending_grammar:
            item["grammarBlock"] = pending_grammar
            item["content"] = pending_intro or ""
            if final_content and final_content != (pending_intro or ""):
                item["contentAfter"] = final_content
            elif final_content and not pending_intro:
                item["contentAfter"] = final_content
            pending_intro = None
            pending_grammar = None
        else:
            item["content"] = pending_intro or final_content
            if pending_intro and final_content and final_content != pending_intro:
                item["contentAfter"] = final_content
            pending_intro = None
            if pending_tools:
                tool = pending_tools[0]
                item["toolName"] = tool["name"]
                if tool["summary"]:
                    item["toolSummary"] = tool["summary"]
                pending_tools = []

        result.append(item)

    return result

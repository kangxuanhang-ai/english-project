import logging
import re

import httpx
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from ai.config import ai_settings

logger = logging.getLogger(__name__)

# --- LLM Cache ---
_llm_cache = {}


def get_llm(deep_think: bool = False) -> ChatDeepSeek:
    """获取缓存的 LLM 实例（按模型类型缓存）"""
    key = "reasoner" if deep_think else "normal"
    if key not in _llm_cache:
        if deep_think:
            _llm_cache[key] = ChatDeepSeek(
                api_key=ai_settings.deepseek_api_key,
                model=ai_settings.deepseek_reasoner_api_model,
                max_tokens=18000,
                streaming=True,
                timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
            )
        else:
            _llm_cache[key] = ChatDeepSeek(
                api_key=ai_settings.deepseek_api_key,
                model=ai_settings.deepseek_api_model,
                temperature=1.3,
                max_tokens=4396,
                streaming=True,
                timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
            )
    return _llm_cache[key]


# --- HTTP Client Singleton ---
_http_client = None


def get_http_client() -> httpx.AsyncClient:
    """获取共享的 HTTP 客户端（模块级单例）"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    return _http_client


async def close_http_client():
    """关闭 HTTP 客户端（应用关闭时调用）"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


# --- Checkpointer ---
_checkpointer_cm = None


async def create_checkpoint() -> AsyncPostgresSaver:
    """初始化 LangGraph checkpointer"""
    global _checkpointer_cm
    _checkpointer_cm = AsyncPostgresSaver.from_conn_string(ai_settings.ai_database_url)
    checkpointer = await _checkpointer_cm.__aenter__()
    await checkpointer.setup()
    return checkpointer


# --- Bocha Search ---
def _sanitize_search_text(text: str, max_len: int = 200) -> str:
    """去除 HTML/控制字符，截断长度，降低 prompt 注入风险。"""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
    cleaned = cleaned.replace("\n", " ").strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "..."
    return cleaned


def _should_auto_web_search(content: str) -> bool:
    """天气、新闻等实时信息类问题自动走联网（无需用户手动点开关）。"""
    text = (content or "").strip()
    if not text:
        return False
    hints = (
        "天气", "气温", "下雨", "下雪", "预报", "风力",
        "新闻", "热搜", "最新", "实时", "今天", "明天", "后天",
        "股价", "汇率", "赛事", "比赛结果",
    )
    return any(h in text for h in hints)


async def create_bocha_search(query: str, count: int = 10) -> str:
    """调用 Bocha 搜索 API（使用共享 HTTP 客户端）"""
    if not (ai_settings.bocha_api_key or "").strip():
        logger.warning("Bocha search skipped: BOCHA_API_KEY is not configured")
        return ""
    try:
        client = get_http_client()
        response = await client.post(
            ai_settings.bocha_search_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ai_settings.bocha_api_key}",
            },
            json={"query": query, "count": count, "summary": True},
        )
        if response.status_code != 200:
            logger.error(
                "Bocha search HTTP %s: %s",
                response.status_code,
                response.text[:500],
            )
            return ""
        data = response.json()
        values = data.get("data", {}).get("webPages", {}).get("value", [])

        if not values:
            logger.info("Bocha search returned no results for query: %s", query[:80])
            return ""

        parts = []
        total_length = 0
        for item in values:
            name = _sanitize_search_text(item.get("name", ""), 120)
            url = _sanitize_search_text(item.get("url", ""), 200)
            site = _sanitize_search_text(item.get("siteName", ""), 80)
            summary = _sanitize_search_text(item.get("summary", ""), 200)
            part = f"""标题：{name}
链接：{url}
摘要：{summary}
网站名称：{site}"""
            if total_length + len(part) > 5000:
                break
            parts.append(part)
            total_length += len(part)

        return "<search_results>\n" + "\n---\n".join(parts) + "\n</search_results>"
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.error(f"Bocha search failed: {e}")
        return ""

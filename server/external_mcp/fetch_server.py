"""Fetch MCP sidecar：内网 HTTP，供 AI 服务 list_tools / call_tool。"""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from ai.services.mcp_url_guard import normalize_fetch_url, validate_fetch_url

logger = logging.getLogger(__name__)

FETCH_MCP_HOST = "0.0.0.0"
FETCH_MCP_PORT = 8080
MAX_RAW_HTML_CHARS = 200_000
MAX_TEXT_CHARS = 8_000
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = 30.0
# 维基等站点会拒绝过于简陋的 UA（403）；需符合常见爬虫/浏览器标识
FETCH_USER_AGENT = (
    "Mozilla/5.0 (compatible; EnglishLearnFetch/1.0; "
    "+https://github.com/english-learning-platform)"
)
FETCH_HEADERS = {
    "User-Agent": FETCH_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class _HtmlTextExtractor(HTMLParser):
    """从 HTML 提取可见文本，跳过 script/style。"""

    _BLOCK_TAGS = frozenset({"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "section", "article"})

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip_depth += 1
        elif tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._parts.append(data)


def html_to_text(html: str) -> str:
    """HTML → 纯文本，供 LLM 注入。"""
    if not html.strip():
        return ""
    parser = _HtmlTextExtractor()
    try:
        parser.feed(html[:MAX_RAW_HTML_CHARS])
        parser.close()
        text = "".join(parser._parts)
    except Exception:
        text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
        text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > MAX_TEXT_CHARS:
        return text[:MAX_TEXT_CHARS] + "\n...[正文已截断]"
    return text


def _transport_security(host: str, port: int) -> TransportSecuritySettings | None:
    if host not in ("0.0.0.0", "::"):
        return None
    allowed_hosts = [
        f"127.0.0.1:{port}",
        f"localhost:{port}",
        "127.0.0.1:*",
        "localhost:*",
        f"fetch-mcp:{port}",
        "fetch-mcp:*",
    ]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=list(dict.fromkeys(allowed_hosts)),
        allowed_origins=[],
    )


def create_fetch_mcp(host: str = FETCH_MCP_HOST, port: int = FETCH_MCP_PORT) -> FastMCP:
    return FastMCP(
        "fetch",
        host=host,
        port=port,
        stateless_http=True,
        transport_security=_transport_security(host, port),
    )


mcp = create_fetch_mcp()


async def _safe_get(url: str) -> str:
    url = normalize_fetch_url(url)
    validate_fetch_url(url)
    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=REQUEST_TIMEOUT,
        headers=FETCH_HEADERS,
    ) as client:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            response = await client.get(current)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    response.raise_for_status()
                current = urljoin(current, location)
                validate_fetch_url(current)
                continue
            response.raise_for_status()
            text = html_to_text(response.text)
            if not text.strip():
                return "（页面无可见正文或抓取为空）"
            return text
    raise ValueError("重定向次数过多")


@mcp.tool()
async def fetch_url(url: str) -> str:
    """抓取允许列表内的英文网页正文（HTML 文本）。仅 http/https，且域名须在白名单内。"""
    try:
        return await _safe_get(url)
    except ValueError as exc:
        return f'{{"error": "{exc}"}}'
    except httpx.HTTPError as exc:
        logger.warning("fetch failed for %s: %s", url, exc)
        return f'{{"error": "抓取失败: {exc}"}}'

"""Fetch 目标 URL 校验：域名白名单 + DNS 私网拦截。"""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

DEFAULT_FETCH_ALLOWLIST = (
    "bbc.com",
    "bbc.co.uk",
    "wikipedia.org",
    "medium.com",
    "nationalgeographic.com",
    "youtube.com",
    "youtu.be",
    "example.com",
    "example.org",
)

_URL_PREFIX_RE = re.compile(r"https?://", re.I)
_VALID_URL_CHARS = re.compile(r"^https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*")


def normalize_fetch_url(raw: str) -> str:
    """去掉链接后误粘连的中文等非 URL 字符（如 ...Flames把这个网页...）。"""
    text = raw.strip()
    if not text:
        return text
    match = _URL_PREFIX_RE.search(text)
    if not match:
        return text
    candidate = text[match.start() :]
    trimmed = _VALID_URL_CHARS.match(candidate)
    if trimmed:
        return trimmed.group(0).rstrip(".,;:!?)\\]")
    return candidate


def _host_allowed(host: str, allowlist: tuple[str, ...]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == suffix or host.endswith("." + suffix) for suffix in allowlist)


def _ip_is_private(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_reserved:
        return True
    if str(addr) == "169.254.169.254":
        return True
    if addr.version == 4:
        return addr.is_private
    # IPv6 不用 is_private：会把 Teredo 等公网地址误判为私网
    return addr in ipaddress.ip_network("fc00::/7")


def _resolve_host_ips(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None)
    return list({info[4][0] for info in infos})


def validate_fetch_url(url: str, allowlist: tuple[str, ...] | None = None) -> None:
    """通过则静默；失败 raise ValueError(中文说明)。"""
    url = normalize_fetch_url(url)
    allowlist = allowlist or DEFAULT_FETCH_ALLOWLIST
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("仅支持 http/https 链接")
    host = parsed.hostname
    if not host:
        raise ValueError("无效 URL")
    if not _host_allowed(host, allowlist):
        raise ValueError("该域名不在允许列表")
    for ip in _resolve_host_ips(host):
        if _ip_is_private(ip):
            raise ValueError("目标地址不允许访问")

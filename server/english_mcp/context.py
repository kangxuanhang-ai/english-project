from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticatedMcpUser:
    user_id: str
    key_prefix: str
    key_hash: str


_mcp_user: ContextVar[AuthenticatedMcpUser | None] = ContextVar("mcp_user", default=None)
_invalid_key_header: ContextVar[bool] = ContextVar("invalid_key_header", default=False)
_client_ip: ContextVar[str] = ContextVar("client_ip", default="unknown")


def get_mcp_user() -> AuthenticatedMcpUser | None:
    return _mcp_user.get()


def set_mcp_user(user: AuthenticatedMcpUser | None) -> None:
    _mcp_user.set(user)


def had_invalid_key_header() -> bool:
    return _invalid_key_header.get()


def set_invalid_key_header(value: bool) -> None:
    _invalid_key_header.set(value)


def get_client_ip() -> str:
    return _client_ip.get()


def set_client_ip(value: str) -> None:
    _client_ip.set(value)

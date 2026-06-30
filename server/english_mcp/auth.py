from english_mcp.config import mcp_settings
from english_mcp.context import get_client_ip, get_mcp_user, had_invalid_key_header
from english_mcp.runtime import is_http_mode


def _env(value: str) -> str | None:
    value = (value or "").strip()
    return value or None


def resolve_progress_user_id() -> tuple[str | None, str | None]:
    """返回 (user_id, error_message)。"""
    if is_http_mode():
        user = get_mcp_user()
        if user:
            return user.user_id, None
        if had_invalid_key_header():
            return None, "ENGLISH-MCP-API-KEY 无效或已吊销"
        return None, "需要 ENGLISH-MCP-API-KEY，请在平台设置页生成"

    api_key = _env(mcp_settings.english_mcp_api_key)
    user_id = _env(mcp_settings.english_mcp_user_id)
    demo_user_id = _env(mcp_settings.english_mcp_demo_user_id)

    if api_key and user_id:
        return user_id, None
    if demo_user_id:
        return demo_user_id, None
    return None, "未配置 ENGLISH_MCP_USER_ID 或 ENGLISH_MCP_DEMO_USER_ID，无法查询学习进度"


def rate_limit_key() -> str:
    if is_http_mode():
        user = get_mcp_user()
        if user:
            return user.key_prefix
        return f"ip:{get_client_ip()}"

    api_key = _env(mcp_settings.english_mcp_api_key)
    if api_key:
        return api_key
    return "anonymous"

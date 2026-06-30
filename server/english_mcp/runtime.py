import os


def is_http_mode() -> bool:
    return os.environ.get("ENGLISH_MCP_HTTP", "").strip() == "1"

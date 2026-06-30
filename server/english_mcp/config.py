from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class MCPSettings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")

    english_mcp_api_key: str = Field(default="", alias="ENGLISH_MCP_API_KEY")
    english_mcp_user_id: str = Field(default="", alias="ENGLISH_MCP_USER_ID")
    english_mcp_demo_user_id: str = Field(default="", alias="ENGLISH_MCP_DEMO_USER_ID")

    mcp_db_pool_size: int = Field(default=5, alias="MCP_DB_POOL_SIZE")
    mcp_db_max_overflow: int = Field(default=10, alias="MCP_DB_MAX_OVERFLOW")
    mcp_http_port: int = Field(default=3002, alias="MCP_HTTP_PORT")
    mcp_http_host: str = Field(default="127.0.0.1", alias="MCP_HTTP_HOST")
    mcp_public_url: str = Field(default="", alias="MCP_PUBLIC_URL")
    mcp_grammar_require_key: bool = Field(default=False, alias="MCP_GRAMMAR_REQUIRE_KEY")

    model_config = {
        "env_file": str(Path(__file__).resolve().parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


mcp_settings = MCPSettings()

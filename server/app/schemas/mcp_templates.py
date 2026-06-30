from pydantic import BaseModel, Field

ALLOWED_MCP_HOSTS = (
    "fetch-mcp",
    "mcp-gateway",
    "localhost",
    "127.0.0.1",
)


class UpdateMcpTemplateDto(BaseModel):
    url: str | None = None
    description: str | None = None
    globallyEnabled: bool | None = None
    headerSchema: dict | None = None
    exposedTools: list[str] | None = None
    fetchUrlAllowlist: list[str] | None = Field(default=None)

from pydantic import BaseModel, Field


class UpsertExternalMcpDto(BaseModel):
    enabled: bool = False
    headers: dict[str, str] = Field(default_factory=dict)

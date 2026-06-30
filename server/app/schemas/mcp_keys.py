from pydantic import BaseModel, Field


class CreateMcpKeyDto(BaseModel):
    name: str = Field(default="", max_length=64)

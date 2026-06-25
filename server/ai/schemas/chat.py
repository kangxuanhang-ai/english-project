from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    role: Literal['normal', 'master', 'business', 'qilinge', 'xiaoman', 'oral'] = "normal"
    deepThink: bool = False
    webSearch: bool = False
    conversationId: str = Field(..., min_length=1)

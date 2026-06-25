from typing import Literal

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    role: Literal['normal', 'master', 'business', 'qilinge', 'xiaoman', 'oral']


class GenerateTitleRequest(BaseModel):
    conversationId: str = Field(..., min_length=1)
    firstMessage: str = Field(..., min_length=1, max_length=500)

from pydantic import BaseModel, Field


class AddWordsDto(BaseModel):
    words: list[str] = Field(min_length=1)


class MarkMasteredDto(BaseModel):
    wordIds: list[str] | None = None
    words: list[str] | None = None


class MyWordItem(BaseModel):
    wordId: str
    word: str
    phonetic: str | None = None
    definition: str | None = None
    translation: str | None = None
    pos: str | None = None
    isMaster: bool
    createdAt: str | None = None


class MyWordListResponse(BaseModel):
    list: list[MyWordItem]
    total: int

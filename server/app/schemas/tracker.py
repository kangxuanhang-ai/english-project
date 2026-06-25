from pydantic import BaseModel, Field


class UvDto(BaseModel):
    anonymousId: str = Field(max_length=128)
    userId: str | None = Field(default=None, max_length=64)
    browser: str | None = Field(default=None, max_length=128)
    os: str | None = Field(default=None, max_length=128)
    device: str | None = Field(default=None, max_length=128)


class UpdateUvDto(BaseModel):
    visitorId: str
    userId: str


class PvDto(BaseModel):
    visitorId: str
    url: str
    referrer: str | None = None
    path: str


class EventDto(BaseModel):
    visitorId: str = Field(max_length=64)
    event: str = Field(max_length=128)
    payload: dict | None = None
    url: str | None = Field(default=None, max_length=2048)


class PerformanceDto(BaseModel):
    visitorId: str = Field(max_length=64)
    fp: float | None = None
    fcp: float | None = None
    lcp: float | None = None
    inp: float | None = None
    cls: float | None = None


class ErrorDto(BaseModel):
    visitorId: str = Field(max_length=64)
    error: str = Field(max_length=512)
    message: str | None = Field(default=None, max_length=2048)
    stack: str | None = Field(default=None, max_length=8192)
    url: str | None = Field(default=None, max_length=2048)

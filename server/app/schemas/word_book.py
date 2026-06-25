from pydantic import BaseModel


class WordQuery(BaseModel):
    page: int = 1
    pageSize: int = 12
    word: str | None = None
    gk: str | None = None
    zk: str | None = None
    gre: str | None = None
    toefl: str | None = None
    ielts: str | None = None
    cet6: str | None = None
    cet4: str | None = None
    ky: str | None = None

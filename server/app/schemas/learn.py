from pydantic import BaseModel


class SaveWordMasterDto(BaseModel):
    wordIds: list[str]

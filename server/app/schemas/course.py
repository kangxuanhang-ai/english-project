from pydantic import BaseModel


class CourseSchema(BaseModel):
    id: str
    name: str
    value: str
    description: str | None = None
    teacher: str
    url: str
    price: str

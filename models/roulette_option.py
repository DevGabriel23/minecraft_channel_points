from pydantic import BaseModel

class RouletteOption(BaseModel):
    name: str
    command: str
    duration: int | None = None
    color: str
    is_bad: bool
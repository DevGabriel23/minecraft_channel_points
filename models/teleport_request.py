from pydantic import BaseModel


class TeleportRequest(BaseModel):
    x: float | None = None
    y: float | None = None
    z: float | None = None
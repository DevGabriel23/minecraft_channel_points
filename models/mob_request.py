from pydantic import BaseModel

class MobRequest(BaseModel):
    mob_type: str
    quantity: int = 1
    r: int = 0
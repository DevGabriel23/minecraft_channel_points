from pydantic import BaseModel

class MobRequest(BaseModel):
    mob_type: str
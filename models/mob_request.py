# Modelo de datos para las solicitudes
from pydantic import BaseModel

class MobRequest(BaseModel):
    mob_type: str
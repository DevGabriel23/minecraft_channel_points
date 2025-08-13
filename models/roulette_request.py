from typing import List
from pydantic import BaseModel
from models.roulette_option import RouletteOption

class RouletteRequest(BaseModel):
    options: List[RouletteOption]
    
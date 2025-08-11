from pydantic import BaseModel


class ItemRequest(BaseModel):
    player_name: str
    item_id: str
    amount: int
from pydantic import BaseModel
from typing import Optional

class PriceRequest(BaseModel):
    chat_id: int
    item_name: str

class PriceResponse(BaseModel):
    chat_id: int
    item_name: str
    current_price: float
    average_price: float
    discount: Optional[bool] = None
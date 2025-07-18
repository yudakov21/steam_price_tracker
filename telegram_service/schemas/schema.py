from pydantic import BaseModel
from typing import Optional, Literal

class PriceRequest(BaseModel):
    chat_id: int
    item_name: str
    check_type: Literal["discount", "increase"] = "discount"

class PriceResponse(BaseModel):
    chat_id: int
    item_name: str
    current_price: float
    average_price: float
    discount: Optional[bool] = None
    increase: Optional[bool] = None

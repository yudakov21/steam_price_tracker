from pydantic import BaseModel


class PriceRequest(BaseModel):
    chat_id: int
    item_name: str

class PriceResponse(BaseModel):
    chat_id: int
    item_name: str
    current_price: float
    average_price: float
    discount: bool | None
# app/schemas/restaurant_schemas.py
from pydantic import BaseModel
from typing import List, Optional


class MenuItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    price: Optional[float] = None


class CartItem(BaseModel):
    id: str
    title: str
    price: float
    quantity: int


class CartResponse(BaseModel):
    cart: List[CartItem] = []
    cart_review_text: Optional[str] = ""
    total: Optional[str] = "0"


class AddToCartRequest(BaseModel):
    selectedItem: str
    quantity: int

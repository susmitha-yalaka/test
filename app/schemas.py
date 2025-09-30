from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models import OrderStatus

# ----- Products / Inventory -----


class CategoryOut(BaseModel):
    id: str
    title: str


class VariantOut(BaseModel):
    id: str  # sku
    title: str
    size: Optional[str] = None
    color: Optional[str] = None


class InventoryAdjustmentIn(BaseModel):
    category: str
    sku: Optional[str] = None
    action: str  # "add" | "remove" | "set"
    qty: int
    notes: Optional[str] = None


class InventoryOut(BaseModel):
    sku: str
    quantity: int

# ----- Orders -----


class OrderItemIn(BaseModel):
    category: str
    item_variant: str  # sku
    size: Optional[str] = None
    color: Optional[str] = None
    quantity: int = 1
    unit_price: Optional[int] = None


class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None

    fulfillment_date: Optional[date] = None
    note: Optional[str] = None
    items: List[OrderItemIn] = []


class OrderOutItem(BaseModel):
    sku: str
    title: str
    quantity: int
    unit_price: Optional[int] = None
    size: Optional[str] = None
    color: Optional[str] = None


class OrderOut(BaseModel):
    id: str
    status: OrderStatus
    created_at: datetime
    customer_name: str
    customer_phone: str
    customer_email: Optional[str]
    customer_address: Optional[str]
    fulfillment_date: Optional[date]
    note: Optional[str]
    items: List[OrderOutItem]
    model_config = ConfigDict(use_enum_values=True)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None


# ----- Flows: data_exchange -----


class DataExchangeIn(BaseModel):
    screen_id: Optional[str] = None
    selected_category: str


class DataExchangeOut(BaseModel):
    # We return an OBJECT with an 'options' array to satisfy your flow schema
    data: dict

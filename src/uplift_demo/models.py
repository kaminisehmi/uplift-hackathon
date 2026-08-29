from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, root_validator, validator


class Customer(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., regex=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    loyalty_points: int = 0

    @validator("name")
    def strip_name(cls, value):
        return value.strip()


class OrderItem(BaseModel):
    sku: str = Field(..., min_length=3)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)

    class Config:
        allow_mutation = False


class Order(BaseModel):
    order_id: str
    customer: Customer
    items: List[OrderItem] = Field(..., min_items=1)
    discount: float = Field(0.0, ge=0)
    created_at: Optional[datetime] = None

    @validator("order_id")
    def order_id_prefix(cls, value):
        if not value.startswith("ORD-"):
            raise ValueError("order_id must start with 'ORD-'")
        return value

    @root_validator
    def discount_not_exceed_subtotal(cls, values):
        items = values.get("items") or []
        subtotal = sum(item.quantity * item.unit_price for item in items)
        if values.get("discount", 0.0) > subtotal:
            raise ValueError("discount cannot exceed subtotal")
        return values

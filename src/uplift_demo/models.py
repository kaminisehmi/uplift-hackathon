from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator  # BC-002, BC-003


class Customer(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")  # BC-004
    loyalty_points: int = 0

    # BC-002
    @field_validator("name")
    @classmethod
    def strip_name(cls, value):
        return value.strip()


class OrderItem(BaseModel):
    sku: str = Field(..., min_length=3)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)

    model_config = ConfigDict(frozen=True)  # BC-003


class Order(BaseModel):
    order_id: str
    customer: Customer
    items: List[OrderItem] = Field(..., min_length=1)  # BC-004
    discount: float = Field(0.0, ge=0)
    created_at: Optional[datetime] = None

    # BC-002
    @field_validator("order_id")
    @classmethod
    def order_id_prefix(cls, value):
        if not value.startswith("ORD-"):
            raise ValueError("order_id must start with 'ORD-'")
        return value

    # BC-002
    @model_validator(mode="after")
    def discount_not_exceed_subtotal(self):
        items = self.items or []
        subtotal = sum(item.quantity * item.unit_price for item in items)
        if (self.discount or 0.0) > subtotal:
            raise ValueError("discount cannot exceed subtotal")
        return self

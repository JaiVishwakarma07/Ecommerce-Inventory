from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

OrderStatus = Literal[
    "pending",
    "processing",
    "shipped",
    "delivered",
    "cancelled",
]


class OrderLineItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(ge=1)
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipping_address: str = Field(min_length=1)
    items: list[OrderLineItemCreate] = Field(min_length=1)

    @field_validator("shipping_address", mode="before")
    @classmethod
    def strip_shipping_address(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()


class OrderLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal

    @field_serializer("unit_price")
    def serialize_unit_price(self, value: Decimal) -> float:
        return float(value)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: OrderStatus
    total_amount: Decimal
    shipping_address: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderLineItemResponse]

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> float:
        return float(value)


class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrderStatus

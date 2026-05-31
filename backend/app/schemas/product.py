from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ProductWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str
    sku: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(ge=0)
    quantity: int = Field(ge=0)
    category: str = Field(min_length=1, max_length=100)
    image_url: str = ""

    @field_validator("image_url", mode="before")
    @classmethod
    def coerce_image_url(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value)

    @field_validator("price")
    @classmethod
    def validate_price_decimal_places(cls, value: Decimal) -> Decimal:
        exponent = value.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -2:
            raise ValueError("price must have at most 2 decimal places")
        return value


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(min_length=1, max_length=255)
    description: str
    sku: str = Field(min_length=1, max_length=255)
    price: Decimal
    quantity: int = Field(ge=0)
    category: str = Field(min_length=1, max_length=100)
    image_url: str = ""
    created_at: datetime
    updated_at: datetime

    @field_validator("image_url", mode="before")
    @classmethod
    def coerce_image_url(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value)

    @field_serializer("price")
    def serialize_price(self, price: Decimal) -> float:
        return float(price)

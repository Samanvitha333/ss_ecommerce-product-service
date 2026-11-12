from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ProductCreate(BaseModel):

    name: str = Field(min_length=2, max_length=150)

    description: str | None = None

    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

    stock_quantity: int = Field(ge=0)


class ProductUpdate(BaseModel):

    name: str | None = Field(default=None, min_length=2, max_length=150)

    description: str | None = None

    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2
    )

    stock_quantity: int | None = Field(default=None, ge=0)


class ProductResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    name: str

    description: str | None

    price: Decimal

    stock_quantity: int

    created_at: datetime

    updated_at: datetime


class AvailabilityResponse(BaseModel):

    product_id: int

    available: bool

    available_quantity: int


class StockReservationRequest(BaseModel):

    order_reference: str = Field(min_length=1, max_length=100)

    quantity: int = Field(gt=0)


class StockReservationResponse(BaseModel):

    reservation_id: str

    order_reference: str

    product_id: int

    quantity: int

    status: str

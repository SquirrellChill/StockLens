from datetime import date, datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict


class InvoiceItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the invoice item")
    quantity: int = Field(..., ge=1, description="Quantity received, must be >= 1")
    unit_price: float = Field(..., ge=0.0, description="Unit cost/price, must be >= 0.0")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v is None:
            raise ValueError("Item name cannot be null")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Item name cannot be empty or contain only whitespace")
        return stripped


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemResponse(InvoiceItemBase):
    id: Optional[int] = None
    product_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    supplier: str = Field(..., min_length=1, max_length=255, description="Supplier or vendor name")
    invoice_number: str = Field(default="—", max_length=100, description="Supplier invoice identifier")
    date: Optional[Union[datetime, date, str]] = None

    @field_validator("supplier")
    @classmethod
    def validate_supplier(cls, v: str) -> str:
        if v is None:
            raise ValueError("Supplier name cannot be null")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Supplier name cannot be empty or contain only whitespace")
        return stripped


class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate] = Field(..., min_length=1, description="Line items on invoice, at least one required")


class InvoiceResponse(BaseModel):
    id: int
    supplier: str
    invoice_number: str
    date: datetime
    total: float
    created_at: datetime
    items: List[InvoiceItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class InvoiceExtractResponse(BaseModel):
    supplier: str = ""
    invoice_number: str = ""
    date: Optional[str] = ""
    items: List[InvoiceItemBase] = Field(default_factory=list)
    raw_text: Optional[str] = ""
    confidence: Optional[float] = None
    requires_review: bool = True
    parsing_notes: List[str] = Field(default_factory=list)

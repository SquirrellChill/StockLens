from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class InvoiceItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the invoice item")
    quantity: int = Field(..., ge=1, description="Quantity received, must be >= 1")
    unit_price: float = Field(..., ge=0.0, description="Unit cost/price, must be >= 0.0")


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemResponse(InvoiceItemBase):
    id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    supplier: str = Field(..., min_length=1, max_length=255, description="Supplier or vendor name")
    invoice_number: str = Field(default="—", max_length=100, description="Supplier invoice identifier")


class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate] = Field(default_factory=list, description="Line items on invoice")


class InvoiceResponse(InvoiceBase):
    id: int
    date: datetime
    total: float
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

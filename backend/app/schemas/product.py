from datetime import date, datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the product")
    quantity: int = Field(..., ge=0, description="Current stock quantity, must be >= 0")
    unit_price: float = Field(..., ge=0.0, description="Unit price, must be >= 0.0")
    expiration_date: Optional[Union[date, str]] = Field(None, description="Expiration date (YYYY-MM-DD) or empty/null")
    alternative_names: List[str] = Field(default_factory=list, description="Alternative names / synonyms for OCR matching")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Product name cannot be empty or blank")
        return stripped

    @field_validator("expiration_date", mode="before")
    @classmethod
    def parse_expiration_date(cls, v: Optional[Union[str, date]]) -> Optional[date]:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            try:
                return date.fromisoformat(v)
            except ValueError:
                raise ValueError("Expiration date must be in YYYY-MM-DD format")
        return v

    @field_validator("alternative_names", mode="before")
    @classmethod
    def sanitize_alternative_names(cls, v: Optional[List[str]]) -> List[str]:
        if not v:
            return []
        if isinstance(v, list):
            cleaned = []
            for item in v:
                if isinstance(item, str):
                    s = item.strip()
                    if s and s not in cleaned:
                        cleaned.append(s)
            return cleaned
        return []


class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    pass


class ProductUpdate(BaseModel):
    """
    Schema for updating an existing product (Edit Product user story).
    Supports updating any or all fields.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    quantity: Optional[int] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0.0)
    expiration_date: Optional[Union[date, str]] = None
    alternative_names: Optional[List[str]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Product name cannot be empty or blank")
            return stripped
        return v

    @field_validator("expiration_date", mode="before")
    @classmethod
    def parse_expiration_date(cls, v: Optional[Union[str, date]]) -> Optional[date]:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            try:
                return date.fromisoformat(v)
            except ValueError:
                raise ValueError("Expiration date must be in YYYY-MM-DD format")
        return v

    @field_validator("alternative_names", mode="before")
    @classmethod
    def sanitize_alternative_names(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        if isinstance(v, list):
            cleaned = []
            for item in v:
                if isinstance(item, str):
                    s = item.strip()
                    if s and s not in cleaned:
                        cleaned.append(s)
            return cleaned
        return []


class ProductResponse(ProductBase):
    """Schema for returned product data."""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

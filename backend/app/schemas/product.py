from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the product")
    quantity: int = Field(..., ge=0, description="Current stock quantity, must be an integer >= 0")
    unit_price: Decimal = Field(..., ge=0, description="Unit price, must be non-negative (zero is allowed)")
    expiration_date: Optional[Union[date, str]] = Field(None, description="Expiration date (YYYY-MM-DD) or empty/null")
    alternative_names: List[str] = Field(default_factory=list, description="Alternative names / synonyms for OCR matching")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v is None:
            raise ValueError("Product name is required")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Product name cannot be empty or contain only whitespace")
        return stripped

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, v: Any) -> int:
        if v is None:
            raise ValueError("Quantity is required")
        if isinstance(v, bool):
            raise ValueError("Quantity must be an integer")
        try:
            if isinstance(v, str):
                v = float(v)
            if isinstance(v, float) and not v.is_integer():
                raise ValueError("Quantity must be an integer")
            iv = int(v)
            if iv < 0:
                raise ValueError("Quantity cannot be negative (zero is allowed)")
            return iv
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError("Quantity must be an integer")

    @field_validator("unit_price", mode="before")
    @classmethod
    def parse_unit_price(cls, v: Union[int, float, str, Decimal]) -> Decimal:
        if v is None or v == "":
            raise ValueError("Unit price is required")
        try:
            d = Decimal(str(v))
            if d < 0:
                raise ValueError("Unit price cannot be negative (zero is allowed)")
            return round(d, 2)
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError("Invalid unit price format")

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
    Schema for updating an existing product.
    Supports partial updates of any product fields without resetting unchanged fields.
    """
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    quantity: Optional[int] = Field(default=None, ge=0)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    expiration_date: Optional[Union[date, str]] = None
    alternative_names: Optional[List[str]] = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            raise ValueError("Product name cannot be null")
        if not isinstance(v, str):
            raise ValueError("Product name must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Product name cannot be empty or contain only whitespace")
        return stripped

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, v: Optional[Any]) -> Optional[int]:
        if v is None:
            raise ValueError("Quantity cannot be null")
        if isinstance(v, bool):
            raise ValueError("Quantity must be an integer")
        try:
            if isinstance(v, str):
                v = float(v)
            if isinstance(v, float) and not v.is_integer():
                raise ValueError("Quantity must be an integer")
            iv = int(v)
            if iv < 0:
                raise ValueError("Quantity cannot be negative (zero is allowed)")
            return iv
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError("Quantity must be an integer")

    @field_validator("unit_price", mode="before")
    @classmethod
    def parse_unit_price(cls, v: Optional[Union[int, float, str, Decimal]]) -> Optional[Decimal]:
        if v is None or v == "":
            raise ValueError("Unit price cannot be null or empty")
        try:
            d = Decimal(str(v))
            if d < 0:
                raise ValueError("Unit price cannot be negative (zero is allowed)")
            return round(d, 2)
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError("Invalid unit price format")

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


class ProductResponse(ProductBase):
    """Schema for returned product data."""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_price")
    def serialize_unit_price(self, v: Union[Decimal, float, int]) -> float:
        """Serializes Decimal monetary value to float in JSON responses for frontend compatibility."""
        return float(round(Decimal(str(v)), 2))

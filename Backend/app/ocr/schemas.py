from pydantic import BaseModel, ConfigDict


class Field(BaseModel):
    value: str | float | None = None   # text for names, number for quantity/prices
    confidence: float = 0.0            # 0-100
    needs_review: bool = False         # True -> highlight for the owner to check


class LineItem(BaseModel):
    row: int
    name: Field
    quantity: Field
    unit_price: Field
    total: Field
    warnings: list[str] = []


class OcrResult(BaseModel):
    method: str                         # "table" or "text"
    invoice_number: str | None = None
    date: str | None = None
    items: list[LineItem]
    warnings: list[str] = []

    # Example shown in Swagger (/docs) instead of "string" placeholders
    model_config = ConfigDict(json_schema_extra={"example": {
        "method": "table",
        "invoice_number": "INV-20418",
        "date": "12/10/2026",
        "items": [
            {"row": 1,
             "name": {"value": "Coca-Cola 330ml", "confidence": 94.0, "needs_review": False},
             "quantity": {"value": 24, "confidence": 96.0, "needs_review": False},
             "unit_price": {"value": 0.45, "confidence": 91.0, "needs_review": False},
             "total": {"value": 10.8, "confidence": 93.0, "needs_review": False},
             "warnings": []},
            {"row": 2,
             "name": {"value": "Angkor Beer can", "confidence": 52.0, "needs_review": True},
             "quantity": {"value": 48, "confidence": 88.0, "needs_review": False},
             "unit_price": {"value": 0.6, "confidence": 45.0, "needs_review": True},
             "total": {"value": 28.8, "confidence": 90.0, "needs_review": False},
             "warnings": ["quantity x unit price = 28.8, but total reads 30"]},
        ],
        "warnings": [],
    }})

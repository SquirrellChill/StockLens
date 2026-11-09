import io
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from ..config import settings
from ..db import get_db
from ..invoice_reader import read_invoice
from ..security import current_user

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


class InvoiceItemIn(BaseModel):
    name: str
    quantity: float
    unit_price: float


class InvoiceIn(BaseModel):
    supplier: Optional[str] = ""
    invoice_number: Optional[str] = ""
    items: List[InvoiceItemIn]
    # Idempotency key from the browser. Retrying a "confirm" with the same key never adds stock twice.
    client_ref: Optional[str] = None


def serialize(inv, items) -> dict:
    return {
        "id": inv["id"],
        "date": inv["date"].isoformat(),
        "supplier": inv["supplier"],
        "invoice_number": inv["invoice_number"],
        "total": float(inv["total"]),
        "items": [{"name": i["name"], "quantity": i["quantity"], "unit_price": float(i["unit_price"])} for i in items],
    }


@router.post("/extract")
def extract(file: UploadFile = File(...), _user=Depends(current_user)):
    """Reads one invoice photo. Saves nothing: the owner reviews and corrects the result first."""
    raw = file.file.read(settings.max_upload_bytes + 1)
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(413, "That image is larger than 10 MB. Please choose a smaller one.")
    try:
        Image.open(io.BytesIO(raw)).verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "We could not read that image. Please upload a JPG, PNG, WebP or HEIC photo.")
    return read_invoice(raw)  # always a usable result; `warnings` explain anything the owner should check


@router.post("", status_code=201)
def confirm_invoice(body: InvoiceIn, response: Response, user=Depends(current_user), db=Depends(get_db)):
    lines = []
    for i in body.items:
        name = i.name.strip()
        if not name:
            continue
        if not (i.quantity > 0) or not float(i.quantity).is_integer() or not (i.unit_price >= 0):
            raise HTTPException(400, f"“{name[:60]}” needs a whole quantity above 0 and a valid price.")
        lines.append({"name": name[:200], "quantity": int(i.quantity), "unit_price": round(float(i.unit_price), 4)})
    if not lines:
        raise HTTPException(400, "Add at least one item before confirming.")
    ref = (body.client_ref or "").strip()[:100] or None
    total = round(sum(l["quantity"] * l["unit_price"] for l in lines), 2)

    with db.transaction():
        inv = db.execute(
            "INSERT INTO invoices (id, user_id, supplier, invoice_number, total, client_ref) VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (user_id, client_ref) WHERE client_ref IS NOT NULL DO NOTHING RETURNING *",
            (str(uuid.uuid4()), user["id"], (body.supplier or "").strip()[:200] or "Unknown supplier",
             (body.invoice_number or "").strip()[:60] or "—", total, ref),
        ).fetchone()
        if inv is None:  # this exact confirm was already saved (e.g. a retry after a dropped connection)
            inv = db.execute("SELECT * FROM invoices WHERE user_id = %s AND client_ref = %s", (user["id"], ref)).fetchone()
            items = db.execute("SELECT * FROM invoice_items WHERE invoice_id = %s ORDER BY id", (inv["id"],)).fetchall()
            response.status_code = 200
            return serialize(inv, items)

        by_name: dict[str, str] = {}
        for p in db.execute("SELECT id, name, alternative_names FROM products WHERE user_id = %s", (user["id"],)):
            for n in [p["name"], *(p["alternative_names"] or [])]:
                by_name.setdefault(n.lower(), p["id"])
        for line in lines:
            pid = by_name.get(line["name"].lower())
            if pid:
                db.execute(
                    "UPDATE products SET quantity = quantity + %s, unit_price = CASE WHEN %s > 0 THEN %s ELSE unit_price END WHERE id = %s",
                    (line["quantity"], line["unit_price"], line["unit_price"], pid),
                )
            else:
                pid = str(uuid.uuid4())
                db.execute(
                    "INSERT INTO products (id, user_id, name, quantity, unit_price) VALUES (%s,%s,%s,%s,%s)",
                    (pid, user["id"], line["name"], line["quantity"], line["unit_price"]),
                )
                by_name[line["name"].lower()] = pid  # a repeated line on the same invoice adds to it
            db.execute(
                "INSERT INTO invoice_items (invoice_id, name, quantity, unit_price) VALUES (%s,%s,%s,%s)",
                (inv["id"], line["name"], line["quantity"], line["unit_price"]),
            )
    items = db.execute("SELECT * FROM invoice_items WHERE invoice_id = %s ORDER BY id", (inv["id"],)).fetchall()
    return serialize(inv, items)


@router.get("")
def list_invoices(user=Depends(current_user), db=Depends(get_db)):
    invs = db.execute("SELECT * FROM invoices WHERE user_id = %s ORDER BY date DESC, seq DESC", (user["id"],)).fetchall()
    by_inv: dict[str, list] = {i["id"]: [] for i in invs}
    if by_inv:
        for it in db.execute("SELECT * FROM invoice_items WHERE invoice_id = ANY(%s) ORDER BY id", (list(by_inv),)):
            by_inv[it["invoice_id"]].append(it)
    return [serialize(i, by_inv[i["id"]]) for i in invs]

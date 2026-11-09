import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from ..db import get_db
from ..security import current_user

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductIn(BaseModel):
    name: str
    quantity: float
    unit_price: float
    expiration_date: Optional[str] = ""
    alternative_names: Optional[List[str]] = None


def serialize(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "quantity": row["quantity"],
        "unit_price": float(row["unit_price"]),
        "expiration_date": row["expiration_date"].isoformat() if row["expiration_date"] else "",
        "alternative_names": row["alternative_names"] or [],
    }


def clean(body: ProductIn) -> dict:
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Please complete all required fields.")
    if len(name) > 200:
        raise HTTPException(400, "Product name is too long.")
    if body.quantity < 0 or body.unit_price < 0:
        raise HTTPException(400, "Please enter a valid non-negative number.")
    if not float(body.quantity).is_integer():
        raise HTTPException(400, "Quantity must be a whole number.")
    if body.quantity > 10_000_000 or body.unit_price > 100_000_000:
        raise HTTPException(400, "That number is too large.")
    exp = (body.expiration_date or "").strip()
    expiry = None
    if exp:
        try:
            expiry = date.fromisoformat(exp)
        except ValueError:
            raise HTTPException(400, "Expiration date must look like YYYY-MM-DD.")
    alts, seen = [], set()
    for n in body.alternative_names or []:
        n = str(n).strip()
        if n and n.lower() not in seen and len(n) <= 200:
            seen.add(n.lower())
            alts.append(n)
    return {
        "name": name,
        "quantity": int(body.quantity),
        "unit_price": round(float(body.unit_price), 4),
        "expiration_date": expiry,
        "alternative_names": Jsonb(alts),
    }


def _get_owned(db, user, product_id: str):
    row = db.execute("SELECT * FROM products WHERE id = %s AND user_id = %s", (product_id, user["id"])).fetchone()
    if not row:
        raise HTTPException(404, "Product not found.")
    return row


@router.get("")
def list_products(user=Depends(current_user), db=Depends(get_db)):
    rows = db.execute("SELECT * FROM products WHERE user_id = %s ORDER BY created_at DESC, seq DESC", (user["id"],)).fetchall()
    return [serialize(r) for r in rows]


@router.get("/{product_id}")
def get_product(product_id: str, user=Depends(current_user), db=Depends(get_db)):
    return serialize(_get_owned(db, user, product_id))


@router.post("", status_code=201)
def create_product(body: ProductIn, user=Depends(current_user), db=Depends(get_db)):
    d = clean(body)
    row = db.execute(
        "INSERT INTO products (id, user_id, name, quantity, unit_price, expiration_date, alternative_names) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *",
        (str(uuid.uuid4()), user["id"], d["name"], d["quantity"], d["unit_price"], d["expiration_date"], d["alternative_names"]),
    ).fetchone()
    return serialize(row)


@router.put("/{product_id}")
def update_product(product_id: str, body: ProductIn, user=Depends(current_user), db=Depends(get_db)):
    d = clean(body)
    row = db.execute(
        "UPDATE products SET name=%s, quantity=%s, unit_price=%s, expiration_date=%s, alternative_names=%s "
        "WHERE id=%s AND user_id=%s RETURNING *",
        (d["name"], d["quantity"], d["unit_price"], d["expiration_date"], d["alternative_names"], product_id, user["id"]),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Product not found.")
    return serialize(row)


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: str, user=Depends(current_user), db=Depends(get_db)):
    cur = db.execute("DELETE FROM products WHERE id = %s AND user_id = %s", (product_id, user["id"]))
    if cur.rowcount == 0:
        raise HTTPException(404, "Product not found.")
    return Response(status_code=204)

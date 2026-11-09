import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..db import get_db
from ..security import current_user

router = APIRouter(prefix="/api/sales", tags=["sales"])


class SaleItemIn(BaseModel):
    product_id: str
    quantity: int
    # name / unit_price may be sent by the client but are ignored: the server uses current product data.
    name: Optional[str] = None
    unit_price: Optional[float] = None


class SaleIn(BaseModel):
    items: List[SaleItemIn]


def serialize(sale, items) -> dict:
    return {
        "id": sale["id"],
        "date": sale["date"].isoformat(),
        "total": float(sale["total"]),
        "items": [
            {"product_id": i["product_id"], "name": i["name"], "quantity": i["quantity"], "unit_price": float(i["unit_price"])}
            for i in items
        ],
    }


@router.post("", status_code=201)
def confirm_sale(body: SaleIn, user=Depends(current_user), db=Depends(get_db)):
    if not body.items:
        raise HTTPException(400, "Add at least one item before confirming.")
    wanted: dict[str, int] = {}
    for item in body.items:
        if item.quantity < 1:
            raise HTTPException(400, "Every item needs a quantity of at least 1.")
        wanted[item.product_id] = wanted.get(item.product_id, 0) + item.quantity

    with db.transaction():
        # Lock the rows (in a fixed order, so two sales can't deadlock) before checking stock.
        products = {
            p["id"]: p
            for p in db.execute(
                "SELECT * FROM products WHERE user_id = %s AND id = ANY(%s) ORDER BY id FOR UPDATE",
                (user["id"], list(wanted)),
            )
        }
        if len(products) != len(wanted):
            raise HTTPException(404, "One of these products no longer exists in your inventory.")
        for pid, qty in wanted.items():
            p = products[pid]
            if qty > p["quantity"]:
                raise HTTPException(409, f"Not enough stock for “{p['name']}” (only {p['quantity']} left).")
        total = round(sum(qty * float(products[pid]["unit_price"]) for pid, qty in wanted.items()), 2)
        sale = db.execute(
            "INSERT INTO sales (id, user_id, total) VALUES (%s,%s,%s) RETURNING *", (str(uuid.uuid4()), user["id"], total)
        ).fetchone()
        for pid, qty in wanted.items():
            p = products[pid]
            db.execute("UPDATE products SET quantity = quantity - %s WHERE id = %s", (qty, pid))
            db.execute(
                "INSERT INTO sale_items (sale_id, product_id, name, quantity, unit_price) VALUES (%s,%s,%s,%s,%s)",
                (sale["id"], pid, p["name"], qty, p["unit_price"]),
            )
    items = db.execute("SELECT * FROM sale_items WHERE sale_id = %s ORDER BY id", (sale["id"],)).fetchall()
    return serialize(sale, items)


@router.get("")
def list_sales(user=Depends(current_user), db=Depends(get_db)):
    sales = db.execute("SELECT * FROM sales WHERE user_id = %s ORDER BY date DESC, seq DESC", (user["id"],)).fetchall()
    by_sale: dict[str, list] = {s["id"]: [] for s in sales}
    if by_sale:
        for i in db.execute("SELECT * FROM sale_items WHERE sale_id = ANY(%s) ORDER BY id", (list(by_sale),)):
            by_sale[i["sale_id"]].append(i)
    return [serialize(s, by_sale[s["id"]]) for s in sales]

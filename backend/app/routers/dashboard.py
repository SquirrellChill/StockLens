from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from ..config import settings
from ..db import get_db
from ..security import current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _money(value: float) -> str:
    return f"${value:,.2f}"


@router.get("")
def summary(
    # JavaScript's Date.getTimezoneOffset(): minutes *behind* UTC (UTC+7 -> -420). Used to define "today".
    tz_offset: int = Query(default=0, ge=-840, le=840),
    user=Depends(current_user),
    db=Depends(get_db),
):
    uid = user["id"]
    shift = timedelta(minutes=-tz_offset)
    local_today = (datetime.now(timezone.utc) + shift).date()

    total_products = db.execute("SELECT COUNT(*) AS c FROM products WHERE user_id = %s", (uid,)).fetchone()["c"]
    low = db.execute(
        "SELECT id, name, quantity FROM products WHERE user_id = %s AND quantity <= %s ORDER BY quantity ASC, name ASC",
        (uid, settings.low_stock_threshold),
    ).fetchall()

    # Fetch a UTC window around "local today", then filter precisely in local time.
    since = datetime.now(timezone.utc) - timedelta(days=2)
    today_sales = 0.0
    for s in db.execute("SELECT date, total FROM sales WHERE user_id = %s AND date >= %s", (uid, since)):
        if (s["date"] + shift).date() == local_today:
            today_sales += float(s["total"])

    activity = []
    for s in db.execute(
        "SELECT s.date, s.total, (SELECT COUNT(*) FROM sale_items WHERE sale_id = s.id) AS n FROM sales s WHERE user_id = %s ORDER BY date DESC LIMIT 5", (uid,)
    ):
        activity.append((s["date"], f"Sale · {s['n']} item{'' if s['n'] == 1 else 's'}", float(s["total"])))
    for i in db.execute("SELECT date, supplier, total FROM invoices WHERE user_id = %s ORDER BY date DESC LIMIT 5", (uid,)):
        activity.append((i["date"], f"Invoice · {i['supplier']}", float(i["total"])))
    activity.sort(key=lambda a: a[0], reverse=True)

    def label(when: datetime) -> str:
        d = when + shift
        return f"{d:%b} {d.day}, {d.year}"

    return {
        "total_products": total_products,
        "today_sales": round(today_sales, 2),
        "low_stock": len(low),
        "low_stock_items": [{"id": r["id"], "name": r["name"], "quantity": r["quantity"]} for r in low[:5]],
        "recent_activity": [{"date": label(d), "title": t, "amount": _money(a)} for d, t, a in activity[:5]],
    }

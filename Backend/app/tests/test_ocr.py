import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from app.ocr.parser import process_invoice, parse_number
from make_samples import make

EXPECTED = [("Coca-Cola", 24, 0.45, 10.8), ("Angkor", 48, 0.6, 28.8),
            ("Mama", 30, 0.18, 5.4), ("Water", 20, 0.35, 7.0)]


def run(name, **kw):
    p = ROOT / name
    make(str(p), **kw)
    return process_invoice(p.read_bytes())


def check(res):
    ok = 0
    for it, (n, q, u, t) in zip(res.items, EXPECTED):
        ok += (n.lower() in (it.name.value or "").lower())
        ok += it.quantity.value == q
        ok += it.unit_price.value is not None and abs(it.unit_price.value - u) < .01
        ok += it.total.value is not None and abs(it.total.value - t) < .01
    return ok, len(EXPECTED) * 4


def test_numbers():
    assert parse_number("#165") == 165 and parse_number("$1,250.50") == 1250.5
    assert parse_number("1.250,50") == 1250.5 and parse_number("abc") is None


def test_grid():
    r = run("g.png"); ok, n = check(r)
    print(r.method, r.invoice_number, r.date, f"{ok}/{n}"); assert r.method == "table" and ok / n >= .8


def test_tilted():
    ok, n = check(run("t.png", angle=2.5)); print("tilted", ok, n); assert ok / n >= .8


def test_text():
    r = run("x.png", grid=False); ok, n = check(r)
    print(r.method, f"{ok}/{n}"); assert r.method == "text" and ok / n >= .75

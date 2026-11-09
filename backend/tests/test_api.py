import io
import os

import pytest
from PIL import Image, ImageDraw, ImageFont

# Tests WIPE the database they connect to, so they only ever use TEST_DATABASE_URL (never DATABASE_URL).
TEST_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_URL or "test" not in TEST_URL.rsplit("/", 1)[-1]:
    pytest.skip("Set TEST_DATABASE_URL to a throw-away database whose name contains 'test'", allow_module_level=True)
os.environ["DATABASE_URL"] = TEST_URL
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DEV_EXPOSE_RESET_CODE"] = "true"
os.environ["ANTHROPIC_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app import invoice_reader  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import get_pool  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        with get_pool().connection() as conn:
            conn.execute("TRUNCATE users CASCADE")
        yield c


def register(client, email="owner@example.com", name="Owner One", password="Passw0rd!"):
    r = client.post("/api/auth/register", json={"full_name": name, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_auth_flow(client):
    s = register(client)
    assert s["user"]["email"] == "owner@example.com" and s["user"]["full_name"] == "Owner One"
    assert client.post("/api/auth/register", json={"full_name": "x", "email": "OWNER@example.com", "password": "Passw0rd!"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "owner@example.com", "password": "nope"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": " Owner@Example.com ", "password": "Passw0rd!"})
    assert r.status_code == 200
    h = auth(r.json()["access_token"])
    assert client.get("/api/auth/me", headers=h).json()["email"] == "owner@example.com"
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth("garbage")).status_code == 401
    assert client.post("/api/auth/register", json={"full_name": "a", "email": "bad", "password": "Passw0rd!"}).status_code == 400
    assert client.post("/api/auth/register", json={"full_name": "a", "email": "a@b.co", "password": "short"}).status_code == 400
    r = client.put("/api/auth/profile", headers=h, json={"full_name": "New Name", "email": "new@example.com"})
    assert r.json()["user"]["name"] == "New Name"


def test_avatar(client):
    token = register(client, "av@example.com")["access_token"]
    buf = io.BytesIO()
    Image.new("RGB", (600, 300), "red").save(buf, "PNG")
    r = client.post("/api/auth/avatar", headers=auth(token), files={"file": ("a.png", buf.getvalue(), "image/png")})
    assert r.status_code == 200 and r.json()["user"]["avatar_url"].startswith("data:image/jpeg;base64,")
    assert client.get("/api/auth/me", headers=auth(token)).json()["avatar_url"]
    assert client.delete("/api/auth/avatar", headers=auth(token)).status_code == 204
    assert client.get("/api/auth/me", headers=auth(token)).json()["avatar_url"] is None
    r = client.post("/api/auth/avatar", headers=auth(token), files={"file": ("a.png", b"not an image", "image/png")})
    assert r.status_code == 400


def test_password_reset(client):
    old = register(client, "reset@example.com")["access_token"]
    unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"}).json()
    assert unknown == {"ok": True}  # no enumeration
    code = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"}).json()["demo_reset_code"]
    body = {"email": "reset@example.com", "code": code, "new_password": "BrandNew123"}
    wrong = "000000" if code != "000000" else "111111"
    assert client.post("/api/auth/reset-password", json={**body, "code": wrong}).status_code == 400
    assert client.post("/api/auth/reset-password", json={**body, "new_password": "short"}).status_code == 400
    assert client.post("/api/auth/reset-password", json=body).json() == {"ok": True}
    assert client.post("/api/auth/reset-password", json=body).status_code == 400  # single use
    assert client.get("/api/auth/me", headers=auth(old)).status_code == 401  # old tokens revoked
    assert client.post("/api/auth/login", json={"email": "reset@example.com", "password": "BrandNew123"}).status_code == 200
    # lockout after 5 wrong attempts
    code = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"}).json()["demo_reset_code"]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert client.post("/api/auth/reset-password", json={**body, "code": wrong}).status_code == 400
    assert client.post("/api/auth/reset-password", json={**body, "code": code}).status_code == 400


def test_password_change_keeps_current_session(client):
    s = register(client, "keep@example.com")
    h = auth(s["access_token"])
    code = client.post("/api/auth/forgot-password", json={"email": "keep@example.com"}).json()["demo_reset_code"]
    r = client.post("/api/auth/reset-password", headers=h, json={"email": "keep@example.com", "code": code, "new_password": "Another123"})
    assert client.get("/api/auth/me", headers=h).status_code == 401  # old token revoked
    fresh = auth(r.json()["access_token"])
    assert client.get("/api/auth/me", headers=fresh).status_code == 200
    # someone else's token must not receive a session for this account
    other = auth(register(client, "other2@example.com")["access_token"])
    code = client.post("/api/auth/forgot-password", json={"email": "keep@example.com"}).json()["demo_reset_code"]
    r = client.post("/api/auth/reset-password", headers=other, json={"email": "keep@example.com", "code": code, "new_password": "Third12345"})
    assert r.status_code == 200 and "access_token" not in r.json()


def test_products_crud_and_isolation(client):
    a = auth(register(client, "a@example.com")["access_token"])
    b = auth(register(client, "b@example.com")["access_token"])
    r = client.post("/api/products", headers=a, json={"name": "Coca-Cola 500ml", "quantity": 48, "unit_price": 1.5, "expiration_date": "", "alternative_names": ["Coke", " ", "coke"]})
    assert r.status_code == 201
    p = r.json()
    assert p["alternative_names"] == ["Coke"] and p["expiration_date"] == "" and p["quantity"] == 48
    assert client.get("/api/products", headers=a).json()[0]["id"] == p["id"]
    assert client.get("/api/products", headers=b).json() == []
    assert client.get(f"/api/products/{p['id']}", headers=b).status_code == 404
    assert client.put(f"/api/products/{p['id']}", headers=b, json={"name": "x", "quantity": 1, "unit_price": 1}).status_code == 404
    assert client.delete(f"/api/products/{p['id']}", headers=b).status_code == 404
    r = client.put(f"/api/products/{p['id']}", headers=a, json={"name": "Coke Zero", "quantity": 10, "unit_price": 2, "expiration_date": "2030-01-31", "alternative_names": []})
    assert r.json()["name"] == "Coke Zero" and r.json()["expiration_date"] == "2030-01-31"
    for bad in ({"name": "", "quantity": 1, "unit_price": 1}, {"name": "x", "quantity": -1, "unit_price": 1},
                {"name": "x", "quantity": 1.5, "unit_price": 1}, {"name": "x", "quantity": 1, "unit_price": 1, "expiration_date": "tomorrow"}):
        assert client.post("/api/products", headers=a, json=bad).status_code in (400, 422)
    assert client.delete(f"/api/products/{p['id']}", headers=a).status_code == 204
    assert client.get(f"/api/products/{p['id']}", headers=a).status_code == 404


def test_sales_invoices_dashboard(client):
    h = auth(register(client, "shop@example.com")["access_token"])
    # invoice creates stock
    inv = client.post("/api/invoices", headers=h, json={"supplier": "Fresh Foods", "invoice_number": "INV-1", "items": [
        {"name": "Milk", "quantity": 10, "unit_price": 1.9}, {"name": "Water", "quantity": 4, "unit_price": 0.6}]})
    assert inv.status_code == 201 and inv.json()["total"] == 21.4
    products = {p["name"]: p for p in client.get("/api/products", headers=h).json()}
    assert products["Milk"]["quantity"] == 10
    # second invoice matches existing product by name (case-insensitive) and adds stock
    client.post("/api/invoices", headers=h, json={"supplier": "", "invoice_number": "", "items": [{"name": "milk", "quantity": 5, "unit_price": 2}]})
    products = {p["name"]: p for p in client.get("/api/products", headers=h).json()}
    assert products["Milk"]["quantity"] == 15 and len(products) == 2
    assert client.post("/api/invoices", headers=h, json={"items": []}).status_code == 400
    assert client.post("/api/invoices", headers=h, json={"items": [{"name": "x", "quantity": 0, "unit_price": 1}]}).status_code == 400

    milk, water = products["Milk"], products["Water"]
    # oversell is refused and changes nothing
    r = client.post("/api/sales", headers=h, json={"items": [{"product_id": milk["id"], "quantity": 1}, {"product_id": water["id"], "quantity": 5}]})
    assert r.status_code == 409 and "Water" in r.json()["detail"]
    assert {p["name"]: p["quantity"] for p in client.get("/api/products", headers=h).json()} == {"Milk": 15, "Water": 4}
    # duplicates merge; price comes from the server, not the client
    r = client.post("/api/sales", headers=h, json={"items": [
        {"product_id": milk["id"], "quantity": 2, "unit_price": 0.01}, {"product_id": milk["id"], "quantity": 1}, {"product_id": water["id"], "quantity": 1}]})
    assert r.status_code == 201
    sale = r.json()
    assert sale["total"] == round(3 * 2 + 0.6, 2) and len(sale["items"]) == 2
    assert {p["name"]: p["quantity"] for p in client.get("/api/products", headers=h).json()} == {"Milk": 12, "Water": 3}
    assert client.post("/api/sales", headers=h, json={"items": [{"product_id": "nope", "quantity": 1}]}).status_code == 404
    assert client.post("/api/sales", headers=h, json={"items": []}).status_code == 400
    assert len(client.get("/api/sales", headers=h).json()) == 1
    assert len(client.get("/api/invoices", headers=h).json()) == 2

    # other users can't sell this shop's products
    other = auth(register(client, "other@example.com")["access_token"])
    assert client.post("/api/sales", headers=other, json={"items": [{"product_id": milk["id"], "quantity": 1}]}).status_code == 404

    d = client.get("/api/dashboard?tz_offset=-420", headers=h).json()
    assert d["total_products"] == 2 and d["today_sales"] == sale["total"]
    assert d["low_stock"] == 1 and d["low_stock_items"][0]["name"] == "Water"
    assert len(d["recent_activity"]) == 3 and d["recent_activity"][0]["amount"].startswith("$")


def _png(lines):
    img = Image.new("RGB", (900, 500), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    for i, line in enumerate(lines):
        d.text((30, 30 + i * 70), line, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_invoice_extract_tesseract_fallback(client):
    h = auth(register(client, "ocr@example.com")["access_token"])
    png = _png(["Fresh Foods Co.", "Invoice No: INV-1042", "Coca Cola 500ml   24   1.50   36.00", "Potato Chips   10   1.20   12.00", "Total 48.00"])
    r = client.post("/api/invoices/extract", headers=h, files={"file": ("inv.png", png, "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["engine"] == "tesseract" and body["supplier"] == "Fresh Foods Co." and body["invoice_number"] == "INV-1042"
    assert [i["quantity"] for i in body["items"]] == [24, 10]
    assert any("basic text recognition" in w for w in body["warnings"])
    assert client.post("/api/invoices/extract", headers=h, files={"file": ("x.png", b"junk", "image/png")}).status_code == 400
    assert client.post("/api/invoices/extract", files={"file": ("inv.png", png, "image/png")}).status_code == 401


def test_invoice_extract_ai(client, monkeypatch):
    h = auth(register(client, "ai@example.com")["access_token"])
    png = _png(["whatever"])
    seen = {}

    def fake(jpeg):
        seen["jpeg"] = jpeg
        return ({
            "supplier": "ក្រុមហ៊ុន ស៊ីម៉ង់ត៍", "invoice_number": "០០១២៣", "currency": "KHR", "printed_total": 100000,
            "items": [
                {"name": "ទឹកសុទ្ធ 500ml", "quantity": "12", "unit_price": 1000},
                {"name": "Coca-Cola 330ml", "quantity": 24, "unit_price": 2000},
                {"name": "  ", "quantity": 1, "unit_price": 1},
                {"name": "Rice 1.5kg", "quantity": 1.5, "unit_price": 3000},
            ],
            "unreadable": ["row 4: price blurred"],
        }, False)

    monkeypatch.setattr(settings, "anthropic_api_key", "sk-test")
    monkeypatch.setattr(invoice_reader, "_call_claude", fake)
    body = client.post("/api/invoices/extract", headers=h, files={"file": ("a.png", png, "image/png")}).json()
    assert body["engine"] == "claude"
    assert [i["name"] for i in body["items"]] == ["ទឹកសុទ្ធ 500ml", "Coca-Cola 330ml", "Rice 1.5kg"]  # Khmer kept as printed, blank row dropped
    assert body["items"][0]["quantity"] == 12 and body["invoice_number"] == "០០១២៣"
    w = " ".join(body["warnings"])
    assert "KHR" in w and "fractional" in w and "add up" in w and "price blurred" in w
    assert seen["jpeg"][:3] == b"\xff\xd8\xff"

    # AI failure -> falls back to Tesseract and says so
    def boom(_):
        raise RuntimeError("api down")

    monkeypatch.setattr(invoice_reader, "_call_claude", boom)
    body = client.post("/api/invoices/extract", headers=h, files={"file": ("a.png", _png(["Shop", "Milk 2 1.00 2.00"]), "image/png")}).json()
    assert body["engine"] == "tesseract" and any("unavailable" in x for x in body["warnings"])


def test_prepare_image_limits_size():
    big = Image.new("RGB", (6000, 3000), "white")
    buf = io.BytesIO()
    big.save(buf, "PNG")
    out = Image.open(io.BytesIO(invoice_reader.prepare_image(buf.getvalue())))
    assert max(out.size) == invoice_reader.MAX_SIDE


def test_parse_khmer_digits_and_thousands():
    r = invoice_reader.parse_invoice_text("Test Shop\nWater ១២ 1,200\n")
    assert r["items"] == [{"name": "Water", "quantity": 12, "unit_price": 1200.0}]


def test_invoice_confirm_is_idempotent(client):
    h = auth(register(client, "idem@example.com")["access_token"])
    body = {"supplier": "S", "invoice_number": "1", "client_ref": "draft-1", "items": [{"name": "Tea", "quantity": 5, "unit_price": 2}]}
    first = client.post("/api/invoices", headers=h, json=body)
    again = client.post("/api/invoices", headers=h, json=body)
    assert first.status_code == 201 and again.status_code == 200 and first.json()["id"] == again.json()["id"]
    assert client.get("/api/products", headers=h).json()[0]["quantity"] == 5  # stock added once
    assert len(client.get("/api/invoices", headers=h).json()) == 1
    # same key from another user is a different invoice
    h2 = auth(register(client, "idem2@example.com")["access_token"])
    assert client.post("/api/invoices", headers=h2, json=body).status_code == 201


def test_cors(client):
    r = client.options("/api/products", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization,content-type"})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "http://localhost:5173"
    r = client.options("/api/products", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers


def test_validation_message_is_text(client):
    r = client.post("/api/auth/login", json={"email": "a@b.co"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)

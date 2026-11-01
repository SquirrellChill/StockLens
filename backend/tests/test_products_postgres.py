import os
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.product import Product


# Get PostgreSQL DATABASE_URL from .env file directly so conftest in-memory override doesn't mask it
from dotenv import dotenv_values
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
env_config = dotenv_values(env_path) if env_path.exists() else {}
PG_DATABASE_URL = env_config.get("DATABASE_URL", "postgresql://postgres:db2907@localhost:5432/stocklens")
if PG_DATABASE_URL.startswith("postgresql://"):
    PG_DATABASE_URL = PG_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)


@pytest.fixture(scope="module")
def pg_engine():
    """Provides an engine connected to PostgreSQL for real persistence testing."""
    if not PG_DATABASE_URL.startswith("postgresql"):
        pytest.skip("PostgreSQL DATABASE_URL not configured")
    try:
        engine = create_engine(PG_DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield engine
        engine.dispose()
    except Exception as exc:
        pytest.skip(f"PostgreSQL server not available: {exc}")


@pytest.fixture(scope="module")
def pg_session_factory(pg_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)


@pytest.fixture(scope="function")
def pg_db(pg_session_factory) -> Session:
    """Provides a session connected directly to PostgreSQL."""
    session = pg_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def pg_client(pg_session_factory):
    """FastAPI TestClient routed to actual PostgreSQL database."""
    def override_get_db():
        session = pg_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_postgres_product_crud_lifecycle(pg_client: TestClient, pg_engine):
    """
    Complete Product Management API lifecycle against actual PostgreSQL:
    1. Create product
    2. Retrieve one product
    3. Retrieve all products
    4. Update product (partial update preserving other fields)
    5. Search product (name & alternative_names)
    6. Delete product
    7. Verify physical persistence and deletion in PostgreSQL using raw SQL
    """
    # 1. Create product
    create_payload = {
        "name": "PG Test Organic Matcha 100g",
        "quantity": 40,
        "unit_price": 18.50,
        "expiration_date": "2027-06-30",
        "alternative_names": ["Green Tea Powder", "Uji Matcha"]
    }
    create_res = pg_client.post("/api/products", json=create_payload)
    assert create_res.status_code == 201, create_res.text
    product_data = create_res.json()
    product_id = product_data["id"]

    assert product_data["name"] == "PG Test Organic Matcha 100g"
    assert product_data["quantity"] == 40
    assert product_data["unit_price"] == 18.50
    assert product_data["expiration_date"] == "2027-06-30"
    assert product_data["alternative_names"] == ["Green Tea Powder", "Uji Matcha"]
    assert "created_at" in product_data
    assert "updated_at" in product_data

    # Verify physical persistence in PostgreSQL via raw SQL
    with pg_engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, name, quantity, unit_price, expiration_date, alternative_names FROM products WHERE id = :pid"),
            {"pid": product_id}
        ).mappings().first()
        assert row is not None, "Product was not found in PostgreSQL table"
        assert row["name"] == "PG Test Organic Matcha 100g"
        assert row["quantity"] == 40
        assert row["unit_price"] == Decimal("18.50")
        assert str(row["expiration_date"]) == "2027-06-30"
        assert "Green Tea Powder" in row["alternative_names"]

    # 2. Retrieve one product
    get_res = pg_client.get(f"/api/products/{product_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "PG Test Organic Matcha 100g"

    # 3. Retrieve all products
    list_res = pg_client.get("/api/products")
    assert list_res.status_code == 200
    all_products = list_res.json()
    assert isinstance(all_products, list)
    matching = [p for p in all_products if p["id"] == product_id]
    assert len(matching) == 1

    # 4. Update product - partial update (only price & quantity changed)
    update_res = pg_client.put(
        f"/api/products/{product_id}",
        json={"unit_price": 19.99, "quantity": 35}
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["unit_price"] == 19.99
    assert updated_data["quantity"] == 35
    # Preserved fields
    assert updated_data["name"] == "PG Test Organic Matcha 100g"
    assert updated_data["expiration_date"] == "2027-06-30"
    assert updated_data["alternative_names"] == ["Green Tea Powder", "Uji Matcha"]

    # Verify updated values persisted in PostgreSQL
    with pg_engine.connect() as conn:
        row = conn.execute(
            text("SELECT quantity, unit_price FROM products WHERE id = :pid"),
            {"pid": product_id}
        ).mappings().first()
        assert row["quantity"] == 35
        assert row["unit_price"] == Decimal("19.99")

    # 5. Search product by primary name
    search_name_res = pg_client.get("/api/products?search=matcha")
    assert search_name_res.status_code == 200
    found_name = search_name_res.json()
    assert any(p["id"] == product_id for p in found_name)

    # Search product by alternative name
    search_alt_res = pg_client.get("/api/products?search=powder")
    assert search_alt_res.status_code == 200
    found_alt = search_alt_res.json()
    assert any(p["id"] == product_id for p in found_alt)

    # 6. Delete product
    del_res = pg_client.delete(f"/api/products/{product_id}")
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True

    # 7. Verify deletion persisted in PostgreSQL
    with pg_engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM products WHERE id = :pid"),
            {"pid": product_id}
        ).first()
        assert row is None, "Product should have been deleted from PostgreSQL"

    # Verify 404 on subsequent GET
    get_deleted = pg_client.get(f"/api/products/{product_id}")
    assert get_deleted.status_code == 404
    assert get_deleted.json() == {"detail": "Product not found."}


def test_postgres_validation_errors(pg_client: TestClient):
    """
    Test validation errors against PostgreSQL-backed application.
    """
    # Negative quantity rejected
    r1 = pg_client.post("/api/products", json={"name": "Bad", "quantity": -5, "unit_price": 2.0})
    assert r1.status_code == 422

    # Negative price rejected
    r2 = pg_client.post("/api/products", json={"name": "Bad", "quantity": 5, "unit_price": -1.0})
    assert r2.status_code == 422

    # Empty name rejected
    r3 = pg_client.post("/api/products", json={"name": "   ", "quantity": 5, "unit_price": 1.0})
    assert r3.status_code == 422

    # 404 on non-existent product
    r4 = pg_client.get("/api/products/9999999")
    assert r4.status_code == 404
    assert r4.json() == {"detail": "Product not found."}

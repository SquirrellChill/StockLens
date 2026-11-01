import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.database import get_db
from app.main import app

# Resolve PostgreSQL DATABASE_URL directly from .env
env_path = Path(__file__).resolve().parent.parent / ".env"
env_config = dotenv_values(env_path) if env_path.exists() else {}
PG_DATABASE_URL = env_config.get(
    "DATABASE_URL",
    "postgresql://postgres:db2907@localhost:5432/stocklens"
)
if PG_DATABASE_URL.startswith("postgresql://"):
    PG_DATABASE_URL = PG_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)


@pytest.fixture(scope="module")
def pg_engine():
    """Provides a PostgreSQL engine for testing."""
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
def pg_client(pg_session_factory):
    """FastAPI TestClient routed directly to the live PostgreSQL database."""
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


@pytest.fixture(scope="function")
def sample_product(pg_client: TestClient, pg_engine):
    """Creates a fresh product in PostgreSQL for each test and ensures cleanup."""
    res = pg_client.post(
        "/api/products",
        json={
            "name": "Original Organic Green Tea 100g",
            "quantity": 25,
            "unit_price": 6.50,
            "expiration_date": "2027-01-15",
            "alternative_names": ["Green Tea", "Loose Leaf Tea"],
        },
    )
    assert res.status_code == 201, f"Failed to create fixture product: {res.text}"
    product = res.json()
    product_id = product["id"]

    yield product

    # Teardown: remove the product from PostgreSQL
    with pg_engine.connect() as conn:
        conn.execute(text("DELETE FROM products WHERE id = :pid"), {"pid": product_id})
        conn.commit()


# ==============================================================================
# VALIDATION TESTS A through K
# ==============================================================================

def test_case_a_update_product_name_successfully(pg_client: TestClient, sample_product, pg_engine):
    """
    Test Case A: Update product name successfully.
    Verifies that name is updated while other fields remain untouched in PostgreSQL.
    """
    pid = sample_product["id"]
    res = pg_client.put(f"/api/products/{pid}", json={"name": "Renamed Premium Green Tea 100g"})

    assert res.status_code == 200
    data = res.json()
    assert data["id"] == pid
    assert data["name"] == "Renamed Premium Green Tea 100g"
    # Unchanged fields preserved
    assert data["quantity"] == 25
    assert data["unit_price"] == 6.50
    assert data["expiration_date"] == "2027-01-15"
    assert data["alternative_names"] == ["Green Tea", "Loose Leaf Tea"]

    # Verify directly in PostgreSQL
    with pg_engine.connect() as conn:
        row = conn.execute(
            text("SELECT name, quantity, unit_price FROM products WHERE id = :pid"),
            {"pid": pid}
        ).mappings().first()
        assert row["name"] == "Renamed Premium Green Tea 100g"
        assert row["quantity"] == 25
        assert row["unit_price"] == Decimal("6.50")


def test_case_b_update_product_quantity_successfully(pg_client: TestClient, sample_product, pg_engine):
    """
    Test Case B: Update product quantity successfully.
    Verifies quantity update in API and PostgreSQL without resetting unchanged fields.
    """
    pid = sample_product["id"]
    res = pg_client.put(f"/api/products/{pid}", json={"quantity": 75})

    assert res.status_code == 200
    data = res.json()
    assert data["quantity"] == 75
    # Name and unit_price remain unchanged
    assert data["name"] == "Original Organic Green Tea 100g"
    assert data["unit_price"] == 6.50

    # Verify directly in PostgreSQL
    with pg_engine.connect() as conn:
        row = conn.execute(
            text("SELECT quantity, name FROM products WHERE id = :pid"),
            {"pid": pid}
        ).mappings().first()
        assert row["quantity"] == 75
        assert row["name"] == "Original Organic Green Tea 100g"


def test_case_c_update_product_price_successfully(pg_client: TestClient, sample_product, pg_engine):
    """
    Test Case C: Update product price successfully.
    Verifies monetary precision storage in PostgreSQL and float serialization in API.
    """
    pid = sample_product["id"]
    res = pg_client.put(f"/api/products/{pid}", json={"unit_price": 8.99})

    assert res.status_code == 200
    data = res.json()
    assert data["unit_price"] == 8.99
    # Unchanged fields preserved
    assert data["name"] == "Original Organic Green Tea 100g"
    assert data["quantity"] == 25

    # Verify directly in PostgreSQL numeric column
    with pg_engine.connect() as conn:
        row = conn.execute(
            text("SELECT unit_price FROM products WHERE id = :pid"),
            {"pid": pid}
        ).mappings().first()
        assert row["unit_price"] == Decimal("8.99")


def test_case_d_update_all_fields_together(pg_client: TestClient, sample_product, pg_engine):
    """
    Test Case D: Update all fields together.
    Verifies changing name, quantity, price, expiration_date, and alternative_names at once.
    """
    pid = sample_product["id"]
    all_fields_payload = {
        "name": "Super Deluxe Matcha Blend 200g",
        "quantity": 120,
        "unit_price": 24.95,
        "expiration_date": "2028-12-31",
        "alternative_names": ["Super Matcha", "Ceremonial Grade"],
    }
    res = pg_client.put(f"/api/products/{pid}", json=all_fields_payload)

    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Super Deluxe Matcha Blend 200g"
    assert data["quantity"] == 120
    assert data["unit_price"] == 24.95
    assert data["expiration_date"] == "2028-12-31"
    assert data["alternative_names"] == ["Super Matcha", "Ceremonial Grade"]

    # Verify all updated fields in PostgreSQL
    with pg_engine.connect() as conn:
        row = conn.execute(
            text("SELECT name, quantity, unit_price, expiration_date, alternative_names FROM products WHERE id = :pid"),
            {"pid": pid}
        ).mappings().first()
        assert row["name"] == "Super Deluxe Matcha Blend 200g"
        assert row["quantity"] == 120
        assert row["unit_price"] == Decimal("24.95")
        assert str(row["expiration_date"]) == "2028-12-31"
        assert row["alternative_names"] == ["Super Matcha", "Ceremonial Grade"]


def test_case_e_reject_empty_product_name(pg_client: TestClient, sample_product, pg_engine):
    """
    Test Case E: Reject empty product name.
    Verifies HTTP 422 and that database record is unchanged.
    """
    pid = sample_product["id"]
    res = pg_client.put(f"/api/products/{pid}", json={"name": ""})

    assert res.status_code == 422
    assert "Product name cannot be empty" in res.text

    # Verify PostgreSQL unchanged
    with pg_engine.connect() as conn:
        row = conn.execute(text("SELECT name FROM products WHERE id = :pid"), {"pid": pid}).mappings().first()
        assert row["name"] == "Original Organic Green Tea 100g"


def test_case_f_reject_whitespace_only_product_name(pg_client: TestClient, sample_product, pg_engine):
    """
    Test Case F: Reject whitespace-only product name.
    Verifies HTTP 422 and that database record is unchanged.
    """
    pid = sample_product["id"]
    res = pg_client.put(f"/api/products/{pid}", json={"name": "     \t   \n   "})

    assert res.status_code == 422
    assert "whitespace" in res.text

    # Verify PostgreSQL unchanged
    with pg_engine.connect() as conn:
        row = conn.execute(text("SELECT name FROM products WHERE id = :pid"), {"pid": pid}).mappings().first()
        assert row["name"] == "Original Organic Green Tea 100g"


def test_case_g_reject_missing_quantity(pg_client: TestClient, sample_product, pg_engine):
    """
    Test Case G: Reject missing quantity.
    Verifies that missing quantity on creation or empty string on update is rejected.
    """
    # 1. On creation: missing quantity is rejected
    create_res = pg_client.post(
        "/api/products",
        json={"name": "No Quantity Tea", "unit_price": 5.0}
    )
    assert create_res.status_code == 422
    assert "quantity" in create_res.text.lower()

    # 2. On update: empty string quantity is rejected
    pid = sample_product["id"]
    update_res = pg_client.put(f"/api/products/{pid}", json={"quantity": ""})
    assert update_res.status_code == 422

    # Verify PostgreSQL unchanged
    with pg_engine.connect() as conn:
        row = conn.execute(text("SELECT quantity FROM products WHERE id = :pid"), {"pid": pid}).mappings().first()
        assert row["quantity"] == 25


def test_case_h_reject_null_quantity(pg_client: TestClient, sample_product, pg_engine):
    """
    Test Case H: Reject null quantity.
    Verifies HTTP 422 and that database record is unchanged.
    """
    pid = sample_product["id"]
    res = pg_client.put(f"/api/products/{pid}", json={"quantity": None})

    assert res.status_code == 422
    assert "Quantity cannot be null" in res.text

    # Verify PostgreSQL unchanged
    with pg_engine.connect() as conn:
        row = conn.execute(text("SELECT quantity FROM products WHERE id = :pid"), {"pid": pid}).mappings().first()
        assert row["quantity"] == 25


def test_case_i_reject_negative_quantity(pg_client: TestClient, sample_product, pg_engine):
    """
    Test Case I: Reject negative quantity.
    Verifies HTTP 422 and that database record is unchanged.
    """
    pid = sample_product["id"]
    res = pg_client.put(f"/api/products/{pid}", json={"quantity": -10})

    assert res.status_code == 422
    assert "Quantity cannot be negative" in res.text

    # Verify PostgreSQL unchanged
    with pg_engine.connect() as conn:
        row = conn.execute(text("SELECT quantity FROM products WHERE id = :pid"), {"pid": pid}).mappings().first()
        assert row["quantity"] == 25


def test_case_j_reject_invalid_price(pg_client: TestClient, sample_product, pg_engine):
    """
    Test Case J: Reject invalid price.
    Tests:
    1. Negative price
    2. Null price
    3. Non-numeric price string
    Verifies HTTP 422 and database protection.
    """
    pid = sample_product["id"]

    # 1. Negative price
    r_neg = pg_client.put(f"/api/products/{pid}", json={"unit_price": -4.99})
    assert r_neg.status_code == 422
    assert "negative" in r_neg.text.lower()

    # 2. Null price
    r_null = pg_client.put(f"/api/products/{pid}", json={"unit_price": None})
    assert r_null.status_code == 422

    # 3. Non-numeric string price
    r_str = pg_client.put(f"/api/products/{pid}", json={"unit_price": "invalid-price"})
    assert r_str.status_code == 422

    # Verify PostgreSQL unit_price unchanged
    with pg_engine.connect() as conn:
        row = conn.execute(text("SELECT unit_price FROM products WHERE id = :pid"), {"pid": pid}).mappings().first()
        assert row["unit_price"] == Decimal("6.50")


def test_case_k_reject_nonexistent_product_id(pg_client: TestClient):
    """
    Test Case K: Reject nonexistent product ID.
    Verifies HTTP 404 with exact detail 'Product not found.' for both GET and PUT.
    """
    non_existent_id = 9999999

    # 1. GET nonexistent product
    get_res = pg_client.get(f"/api/products/{non_existent_id}")
    assert get_res.status_code == 404
    assert get_res.json() == {"detail": "Product not found."}

    # 2. PUT nonexistent product
    put_res = pg_client.put(
        f"/api/products/{non_existent_id}",
        json={"name": "Ghost Product", "quantity": 10}
    )
    assert put_res.status_code == 404
    assert put_res.json() == {"detail": "Product not found."}


# ==============================================================================
# ACCEPTANCE CRITERIA AC1 - AC6 & APPLICATION RESTART PERSISTENCE
# ==============================================================================

def test_acceptance_criteria_ac1_to_ac6_and_restart_persistence(pg_client: TestClient, sample_product, pg_engine):
    """
    End-to-End Acceptance Verification of the Owner User Story:
    AC1: The owner can open a product and see its current information.
    AC2: The owner can change name, quantity, or price and save the changes.
    AC3: Name and quantity cannot be empty.
    AC4: Quantity cannot be negative.
    AC5: After saving, the product list shows the updated information.
    AC6: Changes remain saved after refreshing the browser / app restart.
    """
    pid = sample_product["id"]

    # AC1: Owner can open a product and see its current information
    ac1_res = pg_client.get(f"/api/products/{pid}")
    assert ac1_res.status_code == 200
    current_info = ac1_res.json()
    assert current_info["id"] == pid
    assert current_info["name"] == "Original Organic Green Tea 100g"
    assert current_info["quantity"] == 25
    assert current_info["unit_price"] == 6.50

    # AC3 & AC4: Validation checks (empty name and negative quantity rejected)
    bad_name = pg_client.put(f"/api/products/{pid}", json={"name": ""})
    assert bad_name.status_code == 422

    bad_qty = pg_client.put(f"/api/products/{pid}", json={"quantity": -1})
    assert bad_qty.status_code == 422

    # AC2: Owner can change name, quantity, or price and save the changes
    edit_payload = {
        "name": "Verified Updated Green Tea 100g",
        "quantity": 60,
        "unit_price": 7.25,
    }
    save_res = pg_client.put(f"/api/products/{pid}", json=edit_payload)
    assert save_res.status_code == 200
    saved_info = save_res.json()
    assert saved_info["name"] == "Verified Updated Green Tea 100g"
    assert saved_info["quantity"] == 60
    assert saved_info["unit_price"] == 7.25

    # AC5: After saving, the product list shows the updated information
    list_res = pg_client.get("/api/products")
    assert list_res.status_code == 200
    items = list_res.json()
    updated_in_list = next((p for p in items if p["id"] == pid), None)
    assert updated_in_list is not None, "Edited product must appear in the product list"
    assert updated_in_list["name"] == "Verified Updated Green Tea 100g"
    assert updated_in_list["quantity"] == 60
    assert updated_in_list["unit_price"] == 7.25

    # AC6: Changes remain saved after refreshing the browser / application restart
    # Simulate full application restart by disposing connection pool and opening a new connection
    pg_engine.dispose()
    restarted_engine = create_engine(PG_DATABASE_URL, pool_pre_ping=True)
    with restarted_engine.connect() as conn:
        persisted_row = conn.execute(
            text("SELECT id, name, quantity, unit_price, expiration_date FROM products WHERE id = :pid"),
            {"pid": pid}
        ).mappings().first()
        assert persisted_row is not None
        assert persisted_row["name"] == "Verified Updated Green Tea 100g"
        assert persisted_row["quantity"] == 60
        assert persisted_row["unit_price"] == Decimal("7.25")
        assert str(persisted_row["expiration_date"]) == "2027-01-15"
    restarted_engine.dispose()

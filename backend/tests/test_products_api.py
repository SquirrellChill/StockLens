import pytest
from fastapi.testclient import TestClient


def test_api_edit_product_happy_path(client: TestClient):
    """
    Milestone 2 Main Demonstration: Edit product via PUT /api/products/{id}.
    Verifies full compatibility with frontend productService.update(id, form).
    """
    # 1. First, create a product
    create_res = client.post(
        "/api/products",
        json={
            "name": "Coca-Cola 330ml",
            "quantity": 24,
            "unit_price": 1.25,
            "expiration_date": "2026-10-31",
            "alternative_names": ["Coke", "Coke Regular"],
        },
    )
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # 2. Perform the Edit Product operation
    edit_payload = {
        "name": "Coca-Cola 330ml Can (Pack of 24)",
        "quantity": 30,
        "unit_price": 1.45,
        "expiration_date": "2026-12-31",
        "alternative_names": ["Coke Can", "Classic Coke"],
    }
    edit_res = client.put(f"/api/products/{created_id}", json=edit_payload)

    assert edit_res.status_code == 200
    data = edit_res.json()
    assert data["id"] == created_id
    assert data["name"] == "Coca-Cola 330ml Can (Pack of 24)"
    assert data["quantity"] == 30
    assert data["unit_price"] == 1.45
    assert data["expiration_date"] == "2026-12-31"
    assert data["alternative_names"] == ["Coke Can", "Classic Coke"]

    # 3. Verify changes persist by fetching product
    get_res = client.get(f"/api/products/{created_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Coca-Cola 330ml Can (Pack of 24)"


def test_api_edit_product_edge_cases(client: TestClient):
    """
    Milestone 2 Demonstration: Edge cases for Edit Product.
    - Zero quantity (out of stock)
    - Zero unit price (promotional/free)
    - Clearing expiration date with empty string
    - Emptying alternative names
    """
    create_res = client.post(
        "/api/products",
        json={
            "name": "Promo Energy Drink",
            "quantity": 10,
            "unit_price": 2.50,
            "expiration_date": "2026-08-15",
            "alternative_names": ["Energy", "Booster"],
        },
    )
    product_id = create_res.json()["id"]

    # Edit: set stock to 0, unit price to 0.0, clear expiration date to "", clear synonyms
    edit_payload = {
        "name": "Promo Energy Drink (Out of Stock)",
        "quantity": 0,
        "unit_price": 0.0,
        "expiration_date": "",
        "alternative_names": [],
    }
    edit_res = client.put(f"/api/products/{product_id}", json=edit_payload)
    assert edit_res.status_code == 200
    data = edit_res.json()
    assert data["quantity"] == 0
    assert data["unit_price"] == 0.0
    assert data["expiration_date"] is None
    assert data["alternative_names"] == []


def test_api_edit_product_not_found(client: TestClient):
    """
    Milestone 2: Editing non-existent product returns HTTP 404 with standard error detail.
    """
    res = client.put(
        "/api/products/999999",
        json={"name": "Ghost Item", "quantity": 10, "unit_price": 2.0},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Product not found."


def test_api_edit_product_validation_errors(client: TestClient):
    """
    Milestone 2: Backend validation ensures invalid data is rejected.
    """
    create_res = client.post(
        "/api/products",
        json={"name": "Sample Bread", "quantity": 10, "unit_price": 1.5},
    )
    product_id = create_res.json()["id"]

    # Test negative quantity
    res_neg_qty = client.put(f"/api/products/{product_id}", json={"quantity": -5})
    assert res_neg_qty.status_code == 422

    # Test negative unit price
    res_neg_price = client.put(f"/api/products/{product_id}", json={"unit_price": -2.5})
    assert res_neg_price.status_code == 422

    # Test empty name
    res_empty_name = client.put(f"/api/products/{product_id}", json={"name": "   "})
    assert res_empty_name.status_code == 422

    # Test invalid date format
    res_invalid_date = client.put(f"/api/products/{product_id}", json={"expiration_date": "invalid-date"})
    assert res_invalid_date.status_code == 422


def test_api_create_and_list_products(client: TestClient):
    """
    Verify creating and listing products matches frontend productService.list().
    """
    # Create product 1
    client.post(
        "/api/products",
        json={
            "name": "Whole Milk 1L",
            "quantity": 12,
            "unit_price": 1.9,
            "expiration_date": "2026-11-10",
            "alternative_names": ["Milk"],
        },
    )
    # Create product 2
    client.post(
        "/api/products",
        json={
            "name": "Orange Juice 1L",
            "quantity": 8,
            "unit_price": 2.5,
            "expiration_date": "",
            "alternative_names": ["OJ"],
        },
    )

    list_res = client.get("/api/products")
    assert list_res.status_code == 200
    items = list_res.json()
    assert isinstance(items, list)
    assert len(items) == 2


def test_api_delete_product(client: TestClient):
    """
    Verify deleting product matches frontend productService.remove(id).
    """
    create_res = client.post(
        "/api/products",
        json={"name": "Disposable Cups", "quantity": 100, "unit_price": 0.1},
    )
    product_id = create_res.json()["id"]

    del_res = client.delete(f"/api/products/{product_id}")
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True

    # Check that product is deleted
    get_res = client.get(f"/api/products/{product_id}")
    assert get_res.status_code == 404


def test_health_check(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["service"] == "StockLens API"

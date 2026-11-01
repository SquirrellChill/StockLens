from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.product import Product


def test_product_model_numeric_precision(db_session: Session):
    """
    Verifies that Product.unit_price uses Decimal/Numeric rather than floating point storage.
    """
    product = Product(
        name="Artisan Coffee Beans 250g",
        quantity=15,
        unit_price=Decimal("14.99"),
        expiration_date=None,
        alternative_names=["Coffee", "Beans"]
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    assert isinstance(product.unit_price, Decimal)
    assert product.unit_price == Decimal("14.99")
    assert str(product.unit_price) == "14.99"


def test_product_validation_name(client: TestClient):
    """
    Validation: Product name is required, cannot be empty, cannot contain only whitespace.
    """
    # 1. Missing name
    res_missing = client.post("/api/products", json={"quantity": 10, "unit_price": 5.0})
    assert res_missing.status_code == 422

    # 2. Empty string name
    res_empty = client.post("/api/products", json={"name": "", "quantity": 10, "unit_price": 5.0})
    assert res_empty.status_code == 422

    # 3. Only whitespace name
    res_whitespace = client.post("/api/products", json={"name": "    \t  \n  ", "quantity": 10, "unit_price": 5.0})
    assert res_whitespace.status_code == 422


def test_product_validation_quantity(client: TestClient):
    """
    Validation: Quantity is required when creating, must be an integer, cannot be negative, zero is allowed.
    """
    # 1. Missing quantity
    res_missing = client.post("/api/products", json={"name": "Test Item", "unit_price": 2.5})
    assert res_missing.status_code == 422

    # 2. Negative quantity
    res_neg = client.post("/api/products", json={"name": "Test Item", "quantity": -1, "unit_price": 2.5})
    assert res_neg.status_code == 422

    # 3. Float quantity
    res_float = client.post("/api/products", json={"name": "Test Item", "quantity": 4.5, "unit_price": 2.5})
    assert res_float.status_code == 422

    # 4. Boolean quantity (must not coerce True to 1)
    res_bool = client.post("/api/products", json={"name": "Test Item", "quantity": True, "unit_price": 2.5})
    assert res_bool.status_code == 422

    # 5. Zero quantity is allowed
    res_zero = client.post("/api/products", json={"name": "Out of Stock Item", "quantity": 0, "unit_price": 2.5})
    assert res_zero.status_code == 201
    assert res_zero.json()["quantity"] == 0


def test_product_validation_unit_price(client: TestClient):
    """
    Validation: Unit price is required when creating, cannot be negative, zero is allowed.
    """
    # 1. Missing unit price
    res_missing = client.post("/api/products", json={"name": "Free Sample", "quantity": 50})
    assert res_missing.status_code == 422

    # 2. Negative unit price
    res_neg = client.post("/api/products", json={"name": "Discount Item", "quantity": 10, "unit_price": -0.01})
    assert res_neg.status_code == 422

    # 3. Zero unit price is allowed
    res_zero = client.post("/api/products", json={"name": "Complimentary Item", "quantity": 10, "unit_price": 0.0})
    assert res_zero.status_code == 201
    assert res_zero.json()["unit_price"] == 0.0


def test_nonexistent_product_handling(client: TestClient):
    """
    Consistent JSON error response and 404 status code for non-existent products across GET, PUT, DELETE.
    """
    non_existent_id = 999999

    # 1. GET non-existent
    get_res = client.get(f"/api/products/{non_existent_id}")
    assert get_res.status_code == 404
    assert get_res.json() == {"detail": "Product not found."}

    # 2. PUT non-existent
    put_res = client.put(f"/api/products/{non_existent_id}", json={"name": "Updated Name"})
    assert put_res.status_code == 404
    assert put_res.json() == {"detail": "Product not found."}

    # 3. DELETE non-existent
    del_res = client.delete(f"/api/products/{non_existent_id}")
    assert del_res.status_code == 404
    assert del_res.json() == {"detail": "Product not found."}


def test_product_search_and_crud_lifecycle(client: TestClient):
    """
    Verifies full lifecycle with search functionality:
    - Create multiple items
    - Search by product name
    - Search by alternative name
    - Case-insensitive search
    """
    client.post("/api/products", json={
        "name": "Coca-Cola 330ml Can",
        "quantity": 100,
        "unit_price": 0.85,
        "alternative_names": ["Coke Can", "Classic Soda"]
    })
    client.post("/api/products", json={
        "name": "Pepsi 330ml Can",
        "quantity": 80,
        "unit_price": 0.80,
        "alternative_names": ["Pepsi Cola"]
    })
    client.post("/api/products", json={
        "name": "Spring Water 1.5L",
        "quantity": 50,
        "unit_price": 0.60,
        "alternative_names": ["Mineral Water"]
    })

    # Search by primary name substring
    search_coca = client.get("/api/products?search=coca")
    assert search_coca.status_code == 200
    items_coca = search_coca.json()
    assert len(items_coca) == 1
    assert items_coca[0]["name"] == "Coca-Cola 330ml Can"

    # Search by alternative name
    search_soda = client.get("/api/products?search=soda")
    assert search_soda.status_code == 200
    items_soda = search_soda.json()
    assert len(items_soda) == 1
    assert items_soda[0]["name"] == "Coca-Cola 330ml Can"

    # Search matching multiple items
    search_can = client.get("/api/products?search=can")
    assert search_can.status_code == 200
    items_can = search_can.json()
    assert len(items_can) == 2

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from app.schemas.product import ProductCreate, ProductUpdate
from app.services.product_service import product_service


def test_create_product(db_session: Session):
    data = ProductCreate(
        name="Coca-Cola 500ml",
        quantity=50,
        unit_price=1.5,
        expiration_date="2026-12-31",
        alternative_names=["Coke", "Coca Cola"]
    )
    product = product_service.create(db_session, data)

    assert product.id is not None
    assert product.name == "Coca-Cola 500ml"
    assert product.quantity == 50
    assert product.unit_price == 1.5
    assert product.expiration_date == date(2026, 12, 31)
    assert product.alternative_names == ["Coke", "Coca Cola"]


def test_get_product_by_id(db_session: Session):
    data = ProductCreate(
        name="Instant Noodles",
        quantity=20,
        unit_price=0.75,
        expiration_date=None,
        alternative_names=["Ramen"]
    )
    created = product_service.create(db_session, data)

    fetched = product_service.get_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Instant Noodles"

    not_found = product_service.get_by_id(db_session, 99999)
    assert not_found is None


def test_update_product_full(db_session: Session):
    """
    Main Milestone 2 priority: Verify editing all product fields.
    """
    initial = product_service.create(db_session, ProductCreate(
        name="Original Juice",
        quantity=10,
        unit_price=2.0,
        expiration_date="2026-06-01",
        alternative_names=["Juice"]
    ))

    update_payload = ProductUpdate(
        name="Updated Premium Juice",
        quantity=35,
        unit_price=2.85,
        expiration_date="2026-09-15",
        alternative_names=["Premium Juice", "Orange Drink"]
    )

    updated = product_service.update(db_session, initial.id, update_payload)
    assert updated is not None
    assert updated.id == initial.id
    assert updated.name == "Updated Premium Juice"
    assert updated.quantity == 35
    assert updated.unit_price == Decimal("2.85")
    assert updated.expiration_date == date(2026, 9, 15)
    assert updated.alternative_names == ["Premium Juice", "Orange Drink"]


def test_update_product_partial(db_session: Session):
    """
    Milestone 2: Verify updating partial fields preserves unchanged attributes.
    """
    initial = product_service.create(db_session, ProductCreate(
        name="Whole Milk 1L",
        quantity=15,
        unit_price=1.9,
        expiration_date="2026-11-20",
        alternative_names=["Milk"]
    ))

    # Only update stock quantity and price
    partial_update = ProductUpdate(
        quantity=25,
        unit_price=2.10
    )

    updated = product_service.update(db_session, initial.id, partial_update)
    assert updated is not None
    assert updated.quantity == 25
    assert updated.unit_price == Decimal("2.10")
    # Other fields remain original
    assert updated.name == "Whole Milk 1L"
    assert updated.expiration_date == date(2026, 11, 20)
    assert updated.alternative_names == ["Milk"]


def test_update_product_non_existent(db_session: Session):
    """
    Milestone 2: Verify updating a non-existent product returns None.
    """
    update_payload = ProductUpdate(name="Ghost Product")
    result = product_service.update(db_session, 999999, update_payload)
    assert result is None


def test_get_all_and_search(db_session: Session):
    product_service.create(db_session, ProductCreate(
        name="Potato Chips BBQ",
        quantity=40,
        unit_price=1.2,
        expiration_date=None,
        alternative_names=["Crisps"]
    ))
    product_service.create(db_session, ProductCreate(
        name="Bottled Water 500ml",
        quantity=100,
        unit_price=0.5,
        expiration_date=None,
        alternative_names=["Mineral Water"]
    ))

    all_items = product_service.get_all(db_session)
    assert len(all_items) == 2

    filtered_by_name = product_service.get_all(db_session, search="Chips")
    assert len(filtered_by_name) == 1
    assert filtered_by_name[0].name == "Potato Chips BBQ"

    filtered_by_synonym = product_service.get_all(db_session, search="Mineral")
    assert len(filtered_by_synonym) == 1
    assert filtered_by_synonym[0].name == "Bottled Water 500ml"


def test_delete_product(db_session: Session):
    created = product_service.create(db_session, ProductCreate(
        name="Temporary Snack",
        quantity=5,
        unit_price=1.0,
        expiration_date=None,
        alternative_names=[]
    ))

    success = product_service.delete(db_session, created.id)
    assert success is True

    fetched = product_service.get_by_id(db_session, created.id)
    assert fetched is None

    failed = product_service.delete(db_session, 99999)
    assert failed is False

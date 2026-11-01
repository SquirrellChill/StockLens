import os
import sys
from datetime import date, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, engine, Base
from app.models.product import Product


def seed_demo_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Product).count() > 0:
            print("Database already contains product data. Skipping seed.")
            return

        today = date.today()
        demo_items = [
            Product(
                name="Coca-Cola 500ml",
                quantity=48,
                unit_price=1.50,
                expiration_date=today + timedelta(days=120),
                alternative_names=["Coke", "Coca Cola"],
            ),
            Product(
                name="Instant Noodles",
                quantity=3,
                unit_price=0.80,
                expiration_date=today + timedelta(days=200),
                alternative_names=["Ramen"],
            ),
            Product(
                name="Whole Milk 1L",
                quantity=12,
                unit_price=1.90,
                expiration_date=today + timedelta(days=6),
                alternative_names=["Milk"],
            ),
            Product(
                name="Potato Chips",
                quantity=25,
                unit_price=1.20,
                expiration_date=today + timedelta(days=90),
                alternative_names=["Chips", "Crisps"],
            ),
            Product(
                name="Bottled Water 1L",
                quantity=4,
                unit_price=0.60,
                expiration_date=None,
                alternative_names=["Water"],
            ),
        ]

        db.add_all(demo_items)
        db.commit()
        print(f"Successfully seeded {len(demo_items)} demo products for Milestone 2!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()

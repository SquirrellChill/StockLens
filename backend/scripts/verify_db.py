import os
import sys
from urllib.parse import urlparse

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text
from app.core.config import settings


def verify_database():
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    parsed = urlparse(db_url)
    dialect = parsed.scheme.split("+")[0]

    print("=" * 60)
    print("StockLens Database Connection Verification")
    print("=" * 60)
    print(f"Target Dialect : {dialect}")
    print(f"Host / Server  : {parsed.hostname or 'localhost'}:{parsed.port or 5432}")
    print(f"Database Name  : {parsed.path.lstrip('/') or 'default'}")
    print(f"User           : {parsed.username or 'default'}")
    print("-" * 60)

    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();")).scalar()
            current_db = conn.execute(text("SELECT current_database();")).scalar()
            print("[SUCCESS] Connected to database successfully!")
            print(f"Connected DB   : {current_db}")
            print(f"Server Version : {result}")
            print("=" * 60)
            return True
    except Exception as e:
        print("[FAILED] Could not connect to the target database.")
        print(f"Error Details  : {e}")
        print("-" * 60)
        if "does not exist" in str(e).lower() and parsed.path.lstrip('/'):
            db_name = parsed.path.lstrip('/')
            print(f"NOTE: The database '{db_name}' might not exist yet on this PostgreSQL server.")
            print(f"You can create it by running in PowerShell:")
            print(f'psql -U {parsed.username or "postgres"} -c "CREATE DATABASE {db_name};"')
        elif "password authentication failed" in str(e).lower():
            print("NOTE: Password authentication failed. Please update the password in backend/.env:")
            print('DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/stocklens"')
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = verify_database()
    sys.exit(0 if success else 1)

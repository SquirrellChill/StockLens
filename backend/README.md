# StockLens Backend API Foundation

Backend service for **StockLens**, an inventory management and invoice tracking system built with **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL**, and **Pydantic v2**.

---

## Architecture Overview

```
backend/
├── app/
│   ├── main.py                 # FastAPI application, CORS middleware & lifespan manager
│   ├── core/
│   │   ├── config.py           # Environment settings (Pydantic BaseSettings)
│   │   └── database.py         # SQLAlchemy engine, session maker & connection checks
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── __init__.py         # Model aggregation for Alembic metadata
│   │   ├── base.py             # Declarative Base
│   │   ├── product.py          # Product inventory model
│   │   ├── invoice.py          # Supplier invoice model
│   │   └── invoice_item.py     # Invoice line items model
│   ├── schemas/                # Pydantic v2 request/response validation schemas
│   │   ├── __init__.py         # Schema aggregation
│   │   ├── product.py          # Product schemas (ProductCreate, ProductUpdate, etc.)
│   │   └── invoice.py          # Invoice schemas (InvoiceCreate, InvoiceResponse, etc.)
│   ├── routers/                # HTTP API route handlers
│   │   ├── __init__.py         # API router aggregator mounted at /api
│   │   ├── products.py         # Product CRUD endpoints
│   │   └── invoices.py         # Invoice endpoints
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── product_service.py  # Product operations
│   │   ├── ocr_service.py      # OCR parsing foundation
│   │   └── invoice_service.py  # Invoice operations
│   └── utils/
│       ├── __init__.py
│       └── image_processing.py # Image handling utilities
├── alembic/                    # Database migrations
│   ├── env.py                  # Alembic environment configured to app settings
│   └── versions/               # Migration scripts (products & invoices tables)
├── scripts/
│   ├── verify_db.py            # Verifies PostgreSQL connection and prints server version
│   └── seed.py                 # Seeds initial demo data
├── tests/                      # Automated test suite (Pytest)
│   ├── conftest.py             # In-memory test database fixture
│   ├── test_foundation.py      # Health endpoint, CORS, and DB session tests
│   ├── test_products_api.py    # Product API endpoint tests
│   └── test_product_service.py # Product service unit tests
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic migration configuration
├── .env.example                # Sample environment variables template
└── .env                        # Local environment variables (excluded from Git)
```

---

## Foundation Quickstart (Windows PowerShell)

### 1. Python Environment Setup

Open PowerShell in the project directory:

```powershell
cd D:\CADT\StockLens\backend

# Create virtual environment (Python 3.11+)
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example configuration to `.env`:

```powershell
Copy-Item .env.example .env
```

Open `.env` in your editor and configure your PostgreSQL database credentials:

```env
DATABASE_URL="postgresql://postgres:your_password@localhost:5432/stocklens"
PROJECT_NAME="StockLens API"
BACKEND_CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
```

> **Note**: `.env` is listed in `.gitignore` and is never committed to source control.

### 4. Create Database and Run Migrations

Ensure your local PostgreSQL service is running. If the `stocklens` database does not exist yet, create it:

```powershell
# Using psql to create the database:
psql -U postgres -c "CREATE DATABASE stocklens;"
```

Apply Alembic migrations to create the database tables:

```powershell
alembic upgrade head
```

Verify your database connection with the provided verification script:

```powershell
python scripts/verify_db.py
```

### 5. Start the FastAPI Application

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The server will start at `http://127.0.0.1:8000`.

---

## Verifying Endpoints

### 1. Health Check Endpoint
- **URL**: `http://127.0.0.1:8000/health`
- **Method**: `GET`
- **Response**:
```json
{
  "status": "ok",
  "service": "StockLens API"
}
```

PowerShell test:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

### 2. Interactive API Documentation
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON**: [http://127.0.0.1:8000/api/openapi.json](http://127.0.0.1:8000/api/openapi.json)

---

## Running Automated Tests

Run the full automated test suite (executed in an isolated in-memory database):

```powershell
pytest -v
```

---

## Product Management API Endpoints

All product endpoints are mounted under `/api/products` and conform strictly to the frontend contract (`productService.js`).

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `GET` | `/api/products` | Retrieve all products (supports `?search=...`, `?skip=...`, `?limit=...`) | `200 OK` |
| `GET` | `/api/products/{id}` | Retrieve single product by ID | `200 OK` / `404 Not Found` |
| `POST` | `/api/products` | Create a new product | `201 Created` / `422 Validation Error` |
| `PUT` | `/api/products/{id}` | Update existing product details | `200 OK` / `404 Not Found` |
| `DELETE` | `/api/products/{id}` | Remove a product from inventory | `200 OK` / `404 Not Found` |

### Validation Rules

- **`name`**: Required, cannot be empty or contain only whitespace.
- **`quantity`**: Required when creating, must be an integer, cannot be negative (`>= 0`, zero is allowed).
- **`unit_price`**: Required when creating, must be non-negative (`>= 0.00`, zero is allowed). Stored as `Numeric(10, 2)` / `Decimal`.
- **`expiration_date`**: Optional. If provided, must be `YYYY-MM-DD` or empty string `""` / `null` to clear.
- **`alternative_names`**: Optional array of strings (synonyms for OCR & voice search).

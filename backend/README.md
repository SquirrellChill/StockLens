# StockLens Backend API

Backend service for **StockLens**, an inventory management system featuring OCR invoice scanning.

Developed with:
- **FastAPI** (Python 3.12+)
- **SQLAlchemy 2.0** ORM
- **PostgreSQL** & **SQLite** support
- **Pydantic v2** data validation & schemas
- **Alembic** database migrations
- **Pytest** automated testing
- **OpenCV & Tesseract OCR**

---

## Architecture & Directory Structure

The backend follows Clean Architecture principles, ensuring clear separation between API routes, Pydantic schemas, database models, and business logic:

```
backend/
├── alembic/                    # Database migration scripts
│   ├── env.py                  # Alembic environment configuration
│   └── versions/               # Migration revision files
├── app/
│   ├── main.py                 # FastAPI application entrypoint & middleware
│   ├── core/                   # Core application setup
│   │   ├── config.py           # Environment settings (Pydantic BaseSettings)
│   │   └── database.py         # SQLAlchemy engine, session maker & get_db dependency
│   ├── models/                 # SQLAlchemy ORM database models
│   │   ├── base.py             # Declarative Base
│   │   └── product.py          # Product database table definition
│   ├── schemas/                # Pydantic validation schemas
│   │   └── product.py          # Request & Response models (ProductCreate, ProductUpdate, etc.)
│   ├── services/               # Business logic layer (isolated from HTTP)
│   │   └── product_service.py  # Product queries, updates, and validations
│   └── api/                    # HTTP route handlers
│       ├── deps.py             # Reusable FastAPI dependencies
│       └── v1/
│           ├── router.py       # API v1 router aggregator
│           └── endpoints/
│               └── products.py # Product endpoints (GET, POST, PUT, DELETE)
├── scripts/
│   └── seed.py                 # Seeds initial demo products for Milestone 2
├── tests/                      # Automated test suite
│   ├── conftest.py             # Pytest fixtures and in-memory test database
│   ├── test_product_service.py # Unit tests for service layer
│   └── test_products_api.py    # Integration tests for HTTP endpoints (Edit Product focus)
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic configuration file
├── .env.example                # Sample environment variables template
└── .env                        # Local environment configuration
```

---

## Quickstart Setup

### 1. Create and Activate Virtual Environment

```bash
# Windows
py -3.12 -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Variables Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

By default, `.env` uses SQLite (`sqlite:///./stocklens.db`) for zero-configuration local development. For PostgreSQL, set:
```env
DATABASE_URL="postgresql://postgres:your_password@localhost:5432/stocklens"
```

### 4. Run Migrations & Seed Demo Data

```bash
alembic upgrade head
python scripts/seed.py
```

### 5. Start Backend Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive API documentation will be available at:
- Swagger UI: `http://127.0.0.1:8000/api/docs`
- ReDoc: `http://127.0.0.1:8000/api/redoc`

---

## Running Automated Tests

Run the full Pytest test suite with:

```bash
pytest -v
```

All 14 tests execute against an isolated in-memory SQLite database and test:
- **Milestone 2 Priority**: Edit Product (`PUT /api/products/{id}`) with full payload
- **Edit Product Edge Cases**: partial updates, zero stock, zero price, blanking expiration dates
- **Input Validation**: rejecting negative quantities, negative prices, empty names, and malformed dates
- **Error Handling**: proper HTTP 404 responses for missing products
- **CRUD Operations**: list, get by ID, search by name/synonym, delete

---

## API Endpoints (Product Management)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/products` | List all inventory products (supports `?search=...`, `?skip=...`, `?limit=...`) |
| `GET` | `/api/products/{id}` | Retrieve details for a single product |
| `POST` | `/api/products` | Create a new inventory product |
| `PUT` | `/api/products/{id}` | **Edit product details (Milestone 2 priority)** |
| `DELETE` | `/api/products/{id}` | Remove a product from inventory |
| `GET` | `/health` | Server health check endpoint |

# StockLens Backend API Documentation & Engineering Guide

Production backend and automated invoice ingestion engine for **StockLens**, an intelligent retail inventory management system designed for store owners. Built with **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL**, **Pydantic v2**, **OpenCV**, and **Tesseract OCR**.

---

## 1. Project Overview

StockLens streamlines grocery and retail stock management by combining real-time inventory CRUD operations with automated optical character recognition (OCR) for supplier invoices. Store owners can upload physical or digital supplier invoices (JPG, JPEG, PNG); StockLens validates file integrity, applies OpenCV preprocessing (deskewing, contrast enhancement, denoising, binarization), extracts header and item details via Tesseract OCR and a decoupled layout parser, presents structured items for owner review, and atomically updates stock upon confirmation.

---

## 2. Architecture & Layered Design

StockLens follows an industry-standard layered architecture enforcing clear separation of concerns:

```
┌───────────────────────────────────────────────────────────┐
│              Client Layer (React 19 / Vite 8)             │
└─────────────────────────────┬─────────────────────────────┘
                              │ HTTP / JSON / FormData
                              ▼
┌───────────────────────────────────────────────────────────┐
│                  FastAPI Application (app)                 │
│  - CORS Middleware (Origin check, preflight OPTIONS)       │
│  - Lifespan Startup: PostgreSQL connection check & verify │
└─────────────────────────────┬─────────────────────────────┘
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
┌──────────────────────────────┐ ┌──────────────────────────┐
│   Products Router & Service   │ │ Invoices Router & Service│
│   (/api/products)            │ │ (/api/invoices)          │
│   - List, Search, Filter     │ │ - Upload & Image Validate│
│   - Single Item Fetch        │ │ - OpenCV Preprocessing   │
│   - Create, Update, Delete   │ │ - Tesseract OCR Engine   │
│   - Synonym Lookup           │ │ - Atomic Confirmation    │
└──────────────┬───────────────┘ └───────────┬──────────────┘
               │                             │
               │    SQLAlchemy 2.0 ORM       │
               └──────────────┬──────────────┘
                              ▼
┌───────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                      │
│   - products (numeric price, JSON synonyms)              │
│   - invoices (supplier, invoice_number, total, date)      │
│   - invoice_items (product_id FK, quantity, unit_price)   │
└───────────────────────────────────────────────────────────┘
```

### Architectural Guarantees
1. **Decoupled OCR & Ingestion**: Image validation and text recognition never mutate database state or inventory directly. Every invoice must be reviewed by the owner before confirmation.
2. **Atomic Inventory Integration**: Confirmation creates invoice headers, records line items, matches products by name or alternative names, increments stock, and creates uncatalogued items within a single database transaction. Any failure triggers a complete transaction rollback.
3. **Duplicate Protection**: Re-confirming an invoice from the same supplier with a reliable invoice number is blocked (`409 Conflict`), while cross-supplier number overlaps and unnumbered cash receipts (`"—"`, `"N/A"`) are handled gracefully.

---

## 3. Technology Stack

- **Web Framework:** FastAPI `0.110.0+` (Asynchronous ASGI framework, OpenAPI/Swagger generation)
- **ASGI Server:** Uvicorn `0.28.0+`
- **ORM & Database Toolkit:** SQLAlchemy `2.0.28+`
- **Relational Database:** PostgreSQL 18+ (connected via `psycopg2-binary`)
- **Schema Validation & Serialization:** Pydantic v2 (`pydantic>=2.6.0`, `pydantic-settings>=2.2.0`)
- **Database Migrations:** Alembic `1.13.1+`
- **Computer Vision & Preprocessing:** OpenCV (`opencv-python-headless>=4.9.0`) & Pillow `10.2.0+`
- **OCR Engine:** Tesseract OCR `5.5.0` via `pytesseract`
- **Testing & QA:** Pytest `8.0+`, HTTPX, Starlette TestClient

---

## 4. Project Folder Structure

```
StockLens/
├── backend/
│   ├── alembic/                      # Database migration scripts
│   │   ├── env.py                    # Migration environment tied to SQLAlchemy Base
│   │   └── versions/                 # Versioned migration scripts
│   │       ├── fdc5992b8333_create_products_table.py
│   │       ├── e2a4b8c9d012_create_invoices_tables.py
│   │       └── a5b6c7d8e9f0_add_product_id_to_invoice_items.py
│   ├── app/
│   │   ├── main.py                   # FastAPI app entrypoint, CORS & lifespan
│   │   ├── core/
│   │   │   ├── config.py             # Settings via pydantic-settings (.env loader)
│   │   │   ├── database.py           # Engine, SessionLocal, and DB connectivity checks
│   │   │   └── exceptions.py         # Custom domain exceptions
│   │   ├── models/                   # SQLAlchemy ORM declarative models
│   │   │   ├── product.py            # Product model (name, quantity, unit_price, etc.)
│   │   │   ├── invoice.py            # Invoice model (supplier, invoice_number, total, etc.)
│   │   │   └── invoice_item.py       # InvoiceItem model (FK to invoices & products)
│   │   ├── schemas/                  # Pydantic validation schemas
│   │   │   ├── product.py            # ProductCreate, ProductUpdate, ProductResponse
│   │   │   └── invoice.py            # InvoiceCreate, InvoiceResponse, InvoiceExtractResponse
│   │   ├── routers/                  # API endpoints
│   │   │   ├── products.py           # /api/products CRUD routes
│   │   │   └── invoices.py           # /api/invoices and /api/invoices/extract routes
│   │   ├── services/                 # Core business logic
│   │   │   ├── product_service.py    # Product CRUD operations & pagination
│   │   │   ├── invoice_service.py    # Atomic confirmation, stock updates & duplicate checks
│   │   │   ├── invoice_parser.py     # Deterministic invoice table layout parser
│   │   │   └── ocr_service.py        # Tesseract execution & text extraction
│   │   └── utils/
│   │       ├── image_validation.py   # Magic bytes validation & safe tempfile management
│   │       └── image_processing.py   # OpenCV deskewing, grayscale, contrast & denoising
│   ├── tools/
│   │   └── tesseract/                # Local standalone Tesseract binary distribution
│   │       ├── tesseract.exe
│   │       └── tessdata/
│   ├── tests/                        # Automated Pytest test suite (97 tests)
│   │   ├── conftest.py               # In-memory SQLite fixtures for rapid testing
│   │   ├── test_edit_product_story.py
│   │   ├── test_foundation.py
│   │   ├── test_image_processing.py
│   │   ├── test_image_validation.py
│   │   ├── test_invoice_confirmation.py
│   │   ├── test_invoice_parser.py
│   │   ├── test_invoices_api.py
│   │   ├── test_product_service.py
│   │   ├── test_products.py
│   │   ├── test_products_api.py
│   │   ├── test_products_postgres.py # Direct live PostgreSQL verification
│   │   └── test_samples_preprocessing.py
│   ├── requirements.txt              # Production & test dependencies
│   ├── alembic.ini                   # Alembic configuration file
│   ├── .env.example                  # Environment configuration template
│   └── .env                          # Local secrets and configuration
├── frontend/                         # React 19 + Vite 8 SPA
│   ├── src/
│   │   ├── pages/                    # Products, EditProduct, InvoiceUpload, InvoiceReview
│   │   ├── services/                 # api.js, productService.js, invoiceService.js
│   │   └── components/               # ProductForm, InvoiceTable, Feedback
│   └── package.json
└── sample_invoices/                  # Real-world benchmark invoice images
```

---

## 5. PostgreSQL Configuration & Environment Variables

### Environment File (`backend/.env`)

```env
# Project Identity
PROJECT_NAME="StockLens API"
VERSION="1.0.0"

# PostgreSQL Connection String
DATABASE_URL="postgresql://postgres:haha@localhost:5432/stocklens"

# Allowed CORS Origins (Frontend dev and preview servers)
BACKEND_CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

# Tesseract OCR Executable Path
TESSERACT_CMD="D:\CADT\StockLens\backend\tools\tesseract\tesseract.exe"

# Maximum Image Upload Size (10 MB = 10485760 bytes)
MAX_UPLOAD_SIZE_BYTES=10485760
```

---

## 6. Setup & Installation Guide

### Step 1: Python Environment Setup
Use Python 3.11 or Python 3.12:

```powershell
# Navigate to backend directory
cd D:\CADT\StockLens\backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Tesseract OCR Configuration on Windows
StockLens includes a standalone Tesseract distribution at `backend\tools\tesseract\tesseract.exe`.
Alternatively, you can install Tesseract globally:
1. Download installer from [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install to default location: `C:\Program Files\Tesseract-OCR\tesseract.exe`.
3. Set `TESSERACT_CMD` in `backend/.env`:
   ```env
   TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

### Step 4: Run Database Migrations

Ensure your PostgreSQL service is running:

```powershell
# Run migrations to create products, invoices, and invoice_items tables
alembic upgrade head
```

### Step 5: Start the FastAPI Backend Server

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The server is available at:
- API Base: `http://127.0.0.1:8000`
- Swagger Interactive Documentation: `http://127.0.0.1:8000/docs`
- ReDoc Documentation: `http://127.0.0.1:8000/redoc`

### Step 6: Start the React Frontend

In a separate terminal window:

```powershell
cd D:\CADT\StockLens\frontend
npm install
npm run dev
```

The frontend will run at `http://localhost:5173`.

---

## 7. Running Automated & Integration Tests

### Run Full Pytest Suite (97 Tests)

```powershell
cd D:\CADT\StockLens
backend\.venv\Scripts\python -m pytest backend\tests -v
```

### Run Live Senior QA End-to-End Suite

```powershell
backend\.venv\Scripts\python qa_integration_test.py
```

This verifies all 41 test cases against the live PostgreSQL database, live FastAPI server, and verifies browser console health with Headless Chromium/Edge.

---

## 8. Complete API Endpoint Specification

### Health Check
- **`GET /health`**
  - **Purpose:** Verifies backend liveness.
  - **Response (200 OK):**
    ```json
    { "status": "ok", "service": "StockLens API" }
    ```

---

### Product Management Endpoints

#### 1. Retrieve Products
- **`GET /api/products`**
- **Query Parameters:**
  - `search` (string, optional): Case-insensitive search on `name` or `alternative_names`.
  - `skip` (int, default: 0): Pagination offset.
  - `limit` (int, default: 100): Maximum records returned.
- **Response (200 OK):**
  ```json
  [
    {
      "id": 1,
      "name": "Coca-Cola 500ml",
      "quantity": 48,
      "unit_price": 1.5,
      "expiration_date": "2027-02-28",
      "alternative_names": ["Coke", "Coca Cola"],
      "created_at": "2026-11-01T15:00:00Z",
      "updated_at": "2026-11-01T15:00:00Z"
    }
  ]
  ```

#### 2. Retrieve Single Product
- **`GET /api/products/{id}`**
- **Response (200 OK):** Single product JSON object.
- **Response (404 Not Found):** `{"detail": "Product not found."}`

#### 3. Create Product
- **`POST /api/products`**
- **Request Body:**
  ```json
  {
    "name": "Organic Almond Milk 1L",
    "quantity": 25,
    "unit_price": 3.75,
    "expiration_date": "2027-06-30",
    "alternative_names": ["Almond Milk"]
  }
  ```
- **Response (201 Created):** Created product object with generated `id`.
- **Validation Errors (422 Unprocessable Entity):**
  - Empty or whitespace `name`
  - Negative `quantity` (`quantity < 0`)
  - Negative `unit_price` (`unit_price < 0`)

#### 4. Update Product
- **`PUT /api/products/{id}`**
- **Purpose:** Edit existing product details (supports full or partial updates).
- **Request Body:**
  ```json
  {
    "name": "Organic Almond Milk 1L (Fortified)",
    "quantity": 30,
    "unit_price": 3.99,
    "expiration_date": "2027-07-15",
    "alternative_names": ["Almond Milk", "Fortified Almond Milk"]
  }
  ```
- **Response (200 OK):** Updated product object.
- **Errors:**
  - `404 Not Found`: If product does not exist.
  - `422 Unprocessable Entity`: If `name` is empty or `quantity` is negative.

#### 5. Delete Product
- **`DELETE /api/products/{id}`**
- **Response (200 OK):** `{"ok": true, "message": "Product deleted successfully."}`
- **Errors:** `404 Not Found` if product does not exist.

---

### Invoice & OCR Endpoints

#### 1. Extract Invoice Data (OCR)
- **`POST /api/invoices/extract`**
- **Content-Type:** `multipart/form-data`
- **Request Form:**
  - `file`: Uploaded invoice image (JPG, JPEG, or PNG).
- **Response (200 OK):**
  ```json
  {
    "supplier": "Fresh Foods MarketCo",
    "invoice_number": "INV-2026-9042",
    "date": "2026-10-28",
    "items": [
      {
        "name": "Organic Cavendish Bananas",
        "quantity": 50,
        "unit_price": 0.25
      },
      {
        "name": "Dragon Fruit Fresh",
        "quantity": 20,
        "unit_price": 2.50
      }
    ],
    "raw_text": "...",
    "confidence": 0.88,
    "requires_review": true,
    "parsing_notes": ["Table detected with columns: name, quantity, unit_price"]
  }
  ```
- **Errors:**
  - `400 Bad Request`: Empty file, corrupted image, or unsupported image format.
  - `413 Payload Too Large`: Image file exceeds 10 MB.
  - `503 Service Unavailable`: Tesseract OCR executable not found on server.

#### 2. Confirm Invoice & Sync Stock
- **`POST /api/invoices`**
- **Purpose:** Atomically confirms reviewed invoice, links items, updates existing product stock, and creates new catalog items.
- **Request Body:**
  ```json
  {
    "supplier": "Fresh Foods MarketCo",
    "invoice_number": "INV-2026-9042",
    "date": "2026-10-28T00:00:00Z",
    "items": [
      {
        "name": "Organic Cavendish Bananas",
        "quantity": 50,
        "unit_price": 0.25
      }
    ]
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "id": 14,
    "supplier": "Fresh Foods MarketCo",
    "invoice_number": "INV-2026-9042",
    "date": "2026-10-28T00:00:00Z",
    "total": 12.50,
    "created_at": "2026-11-01T17:30:00Z",
    "items": [
      {
        "id": 28,
        "product_id": 182,
        "name": "Organic Cavendish Bananas",
        "quantity": 50,
        "unit_price": 0.25
      }
    ]
  }
  ```
- **Errors:**
  - `400 Bad Request`: Empty items list, missing name, or negative price/quantity.
  - `409 Conflict`: Duplicate confirmation detected for reliable `(supplier, invoice_number)`.

#### 3. List Confirmed Invoices
- **`GET /api/invoices`**
- **Query Parameters:** `skip` (default 0), `limit` (default 100).
- **Response (200 OK):** List of confirmed invoices with line items, sorted newest first.

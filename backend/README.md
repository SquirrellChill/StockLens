# StockLens Backend

FastAPI + **Postgres**. Accounts (JWT), products, sales (stock deducted atomically),
supplier invoices with **batch upload** and **AI reading for Khmer + English**, dashboard summary, profile photo,
password reset by emailed 6-digit code.

## Run it

```bash
cd backend
docker compose up -d                                     # local Postgres
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # already set up for the docker database (port 5433)
python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs · health check: http://localhost:8000/api/health
Tables are created automatically on startup (the same SQL is in `schema.sql`).

Then the frontend: `cd frontend && cp .env.example .env && npm install && npm run dev` (http://localhost:5173).
Leave `VITE_API_BASE_URL` empty in `frontend/.env` for the browser-only demo mode.

## Database setup

The API needs a PostgreSQL database and a login for it, set in `backend/.env` as `DATABASE_URL`.
Pick **one** of these:

**A. Docker** (nothing else to install). `docker compose up -d` starts Postgres on port **5433** with user
`stocklens`, password `stocklens`, database `stocklens`, which is exactly what `.env.example` contains.

**B. PostgreSQL installed on your computer** (Windows installer, pgAdmin, etc.). Create a user and database once,
using pgAdmin's *Query Tool*, or `psql` (on Windows: `"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres`,
the number is your version):

```sql
CREATE USER stocklens WITH PASSWORD 'stocklens';
CREATE DATABASE stocklens OWNER stocklens;
```

then set `DATABASE_URL=postgresql://stocklens:stocklens@localhost:5432/stocklens` (use your own port if it isn't 5432).
Or skip the new user and use the one you already have: create an empty database called `stocklens` and set
`DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/stocklens`
(if the password contains `@ : / # %`, write them as `%40 %3A %2F %23 %25`).

Tables are created automatically on the first start.

### "password authentication failed for user stocklens"

PostgreSQL is running but doesn't know that user/password. This usually means a PostgreSQL installed on your computer
is answering on port 5432, not the Docker one. Follow option B above (or option A, which uses port 5433 to avoid the clash).
Other messages the API prints: *database does not exist* -> run `CREATE DATABASE stocklens;`;
*can't reach PostgreSQL* -> start Docker / the PostgreSQL service and check the port.

## Invoice reading (Khmer + English)

`POST /api/invoices/extract` reads **one photo** and returns `{ supplier, invoice_number, items[], currency,
printed_total, items_total, engine, warnings[] }`. It saves nothing; the owner reviews first.

| Engine | When | Notes |
| --- | --- | --- |
| **AI vision** (Claude) | `ANTHROPIC_API_KEY` is set | Handles Khmer, English, mixed, tilted or faded photos. Reads every line, keeps names in the original script, converts Khmer digits. Photos are sent to the Anthropic API. |
| **Tesseract** `khm+eng` | no key, or the AI call fails | Free and offline, much less accurate on real photos. Needs `tesseract` plus the language packs: `sudo apt install tesseract-ocr tesseract-ocr-khm` (macOS: `brew install tesseract tesseract-lang`). |

To help catch missed lines the response compares the sum of the items with the total printed on the invoice and adds
a warning when they differ. It also warns about non-USD invoices (StockLens shows USD), fractional quantities and
hard-to-read lines. The frontend uploads several photos at once (3 are read in parallel) and lets the owner
re-upload a photo or add another page to the same invoice.

`POST /api/invoices` accepts an optional `client_ref`. Saving the same `client_ref` twice returns the first invoice and
does not add stock again, so a retry after a dropped connection is safe.

## Settings (`.env`)

See `.env.example`. The important ones: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `SECRET_KEY`, `CORS_ORIGINS`,
`DEV_EXPOSE_RESET_CODE` (development only), `SMTP_*`.

## Endpoints

All `/api/*` routes except `/api/auth/register|login|forgot-password|reset-password` need `Authorization: Bearer <token>`.
Every row belongs to one user; users never see each other's data.

| Method & path | What it does |
| --- | --- |
| `POST /api/auth/register` · `login` | Returns `{ access_token, user }` |
| `GET /api/auth/me` · `PUT /api/auth/profile` | Current user / update name + email |
| `POST` · `DELETE /api/auth/avatar` | Upload (multipart `file`) or remove profile photo |
| `POST /api/auth/forgot-password` · `reset-password` | Emailed 6-digit code, 10 min expiry, 5 attempts |
| `GET/POST /api/products`, `GET/PUT/DELETE /api/products/{id}` | Inventory |
| `POST /api/sales` · `GET /api/sales` | Confirm a sale (checks and deducts stock) / history |
| `POST /api/invoices/extract` | Read one invoice photo (see above) |
| `POST /api/invoices` · `GET /api/invoices` | Confirm an invoice (adds stock, creates unknown products) / history |
| `GET /api/dashboard?tz_offset=` | Totals, low-stock items, recent activity |

## Tests

They wipe the database they use, so point them at a throw-away database whose name contains `test`:

```bash
createdb stocklens_test    # or create it inside the docker database
TEST_DATABASE_URL=postgresql://stocklens:stocklens@localhost:5432/stocklens_test python -m pytest -q
```

## Before deploying

Set `SECRET_KEY`, `CORS_ORIGINS`, `DEV_EXPOSE_RESET_CODE=false`, SMTP, serve over HTTPS, and consider rate-limiting
`/api/auth/*` (not included).

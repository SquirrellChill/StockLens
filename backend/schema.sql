-- StockLens schema (Postgres). Safe to run more than once.
-- The API creates these automatically on startup; this file is the same SQL for reference.

CREATE TABLE IF NOT EXISTS users (
  id            text PRIMARY KEY,
  name          text NOT NULL,
  email         text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  token_version integer NOT NULL DEFAULT 0,
  avatar        text,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS resets (
  id         bigserial PRIMARY KEY,
  user_id    text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code_hash  text NOT NULL,
  attempts   integer NOT NULL DEFAULT 0,
  expires_at double precision NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
  id                text PRIMARY KEY,
  user_id           text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name              text NOT NULL,
  quantity          integer NOT NULL CHECK (quantity >= 0),
  unit_price        numeric(14,4) NOT NULL CHECK (unit_price >= 0),
  expiration_date   date,
  alternative_names jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  seq               bigserial
);
CREATE INDEX IF NOT EXISTS idx_products_user ON products(user_id, created_at DESC, seq DESC);

CREATE TABLE IF NOT EXISTS sales (
  id      text PRIMARY KEY,
  user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date    timestamptz NOT NULL DEFAULT now(),
  total   numeric(14,2) NOT NULL,
  seq     bigserial
);
CREATE INDEX IF NOT EXISTS idx_sales_user ON sales(user_id, date DESC);

CREATE TABLE IF NOT EXISTS sale_items (
  id         bigserial PRIMARY KEY,
  sale_id    text NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
  product_id text,                       -- no FK: history survives deleting a product
  name       text NOT NULL,
  quantity   integer NOT NULL,
  unit_price numeric(14,4) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale ON sale_items(sale_id);

CREATE TABLE IF NOT EXISTS invoices (
  id             text PRIMARY KEY,
  user_id        text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date           timestamptz NOT NULL DEFAULT now(),
  supplier       text NOT NULL,
  invoice_number text NOT NULL,
  total          numeric(14,2) NOT NULL,
  client_ref     text,                   -- idempotency key: a retried "confirm" never adds stock twice
  seq            bigserial
);
CREATE INDEX IF NOT EXISTS idx_invoices_user ON invoices(user_id, date DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_invoices_client_ref ON invoices(user_id, client_ref) WHERE client_ref IS NOT NULL;

CREATE TABLE IF NOT EXISTS invoice_items (
  id         bigserial PRIMARY KEY,
  invoice_id text NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  name       text NOT NULL,
  quantity   integer NOT NULL,
  unit_price numeric(14,4) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id);

from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urlparse

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "schema.sql"
_pool: Optional[ConnectionPool] = None


def explain_connection_error(url: str, error: Exception) -> str:
    """Turns a raw Postgres connection failure into something a person can act on."""
    u = urlparse(url)
    where = f"{u.hostname or 'localhost'}:{u.port or 5432}"
    dbname = (u.path or "/").lstrip("/") or "postgres"
    user = u.username or "?"
    raw = str(error).lower()
    if "password authentication failed" in raw or "authentication failed" in raw:
        why = (
            f"PostgreSQL is running at {where}, but it rejected the user name or password in DATABASE_URL "
            f"(user \"{user}\").\n"
            "Either that user doesn't exist in this PostgreSQL, or its password is different. If you installed "
            "PostgreSQL on this computer yourself, it is probably the one answering on this port, with your own "
            "\"postgres\" password.\n"
            "Fix: create the user and database in it (README -> \"Database setup\"), or put your own login in "
            "backend/.env, e.g.\n"
            f"    DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@{where}/{dbname}"
        )
    elif "does not exist" in raw and "database" in raw:
        why = (
            f"PostgreSQL at {where} is reachable, but the database \"{dbname}\" doesn't exist yet.\n"
            f"Create it (pgAdmin, or psql):   CREATE DATABASE {dbname};"
        )
    elif "refused" in raw or "could not connect" in raw or "timeout" in raw or "timed out" in raw or "name or service" in raw:
        why = (
            f"Can't reach PostgreSQL at {where}. Start it first: `docker compose up -d` in the backend folder, "
            "or start the PostgreSQL service on your computer. Then check the host and port in DATABASE_URL."
        )
    else:
        why = f"Could not connect to PostgreSQL at {where}: {str(error).strip().splitlines()[0] if str(error).strip() else error}"
    return f"\n\nStockLens could not open its database.\n{why}\n"


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not set. Put your Postgres connection string in backend/.env "
                "(see .env.example)."
            )
        # Try once, with a short timeout, so a wrong password gives one clear message instead of 20s of retries.
        try:
            psycopg.connect(settings.database_url, connect_timeout=5).close()
        except psycopg.OperationalError as e:
            raise RuntimeError(explain_connection_error(settings.database_url, e)) from None
        _pool = ConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=settings.db_pool_size,
            timeout=15,
            open=False,
            kwargs={
                # autocommit: every statement is durable at once; multi-step work uses `with db.transaction():`
                "autocommit": True,
                "row_factory": dict_row,
            },
        )
        _pool.open(wait=True, timeout=20)
    return _pool


def init_db() -> None:
    with get_pool().connection() as conn:
        conn.execute(SCHEMA_FILE.read_text())


def close_db() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_db() -> Iterator[Connection]:
    with get_pool().connection() as conn:
        yield conn

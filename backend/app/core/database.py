from typing import Generator
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

# Normalize PostgreSQL driver if needed:
# If user provided 'postgresql://', normalize to 'postgresql+psycopg2://'
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Engine configuration supporting PostgreSQL and SQLite
connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
else:
    # PostgreSQL connection pooling optimizations
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(
    db_url,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base for all models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a SQLAlchemy database session per request.
    Ensures connection is returned to pool or closed properly.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Verifies database connectivity by executing a lightweight query.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

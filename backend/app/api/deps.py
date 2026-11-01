from typing import Generator
from sqlalchemy.orm import Session
from app.core.database import get_db

# Re-export get_db as the standard dependency for endpoints
__all__ = ["get_db", "Session"]

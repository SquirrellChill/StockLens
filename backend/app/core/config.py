import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_file = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "StockLens API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # PostgreSQL Database URL
    # Format: postgresql://<username>:<password>@<host>:<port>/<database>
    DATABASE_URL: str = "postgresql://postgres:db2907@localhost:5432/stocklens"

    # CORS configuration for Vite frontend
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # OCR configuration
    TESSERACT_CMD: str = "tesseract"

    # Image upload and validation configuration
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit matching frontend
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png"]
    ALLOWED_IMAGE_MIMES: List[str] = ["image/jpeg", "image/png"]
    ALLOWED_IMAGE_FORMATS: List[str] = ["JPEG", "PNG"]

    model_config = SettingsConfigDict(
        env_file=str(_env_file) if _env_file.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

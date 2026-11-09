import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _secret_key() -> str:
    key = os.getenv("SECRET_KEY")
    if key:
        return key
    path = BASE_DIR / "data" / ".secret_key"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_text().strip()
    key = secrets.token_urlsafe(48)
    path.write_text(key)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


class Settings:
    database_url = os.getenv("DATABASE_URL", "")
    db_pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
    secret_key = _secret_key()
    token_ttl_days = int(os.getenv("TOKEN_TTL_DAYS", "7"))
    cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    # localhost / 127.0.0.1 / private-LAN addresses on any port (Vite dev + preview servers)
    cors_origin_regex = os.getenv(
        "CORS_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?$",
    )
    dev_expose_reset_code = _flag("DEV_EXPOSE_RESET_CODE", False)
    reset_ttl_minutes = 10
    reset_max_attempts = 5
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", "StockLens <no-reply@stocklens.local>")
    max_upload_bytes = 10 * 1024 * 1024

    # --- invoice reading ---
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    # auto = AI when a key is set, else Tesseract | claude = AI only | tesseract = Tesseract only
    ocr_engine = os.getenv("OCR_ENGINE", "auto").lower()
    tesseract_langs = [l for l in os.getenv("TESSERACT_LANGS", "khm+eng").split("+") if l]
    low_stock_threshold = 5


settings = Settings()

import hashlib
import hmac
import re
import secrets
import time
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException

from .config import settings
from .db import get_db

PBKDF2_ITERATIONS = 240_000
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
MIN_PASSWORD = 8
MAX_PASSWORD = 128


def normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def check_email(value: str) -> str:
    email = normalize_email(value)
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(400, "Please enter a valid email address.")
    return email


def check_password(value: str) -> str:
    if not value:
        raise HTTPException(400, "Password is required.")
    if len(value) < MIN_PASSWORD:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD} characters.")
    if len(value) > MAX_PASSWORD:
        raise HTTPException(400, f"Password must be at most {MAX_PASSWORD} characters.")
    return value


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(candidate, digest)
    except Exception:
        return False


def hash_code(code: str) -> str:
    return hmac.new(settings.secret_key.encode(), code.encode(), hashlib.sha256).hexdigest()


def create_token(user) -> str:
    now = int(time.time())
    payload = {
        "sub": user["id"],
        "tv": user["token_version"],
        "iat": now,
        "exp": now + settings.token_ttl_days * 86400,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def public_user(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "full_name": row["name"],
        "email": row["email"],
        "avatar_url": row["avatar"] or None,
    }


def token_subject(authorization: Optional[str]) -> Optional[str]:
    """User id inside a (possibly outdated) bearer token, or None. Does not check token_version."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return jwt.decode(authorization[7:].strip(), settings.secret_key, algorithms=["HS256"]).get("sub")
    except jwt.PyJWTError:
        return None


def current_user(authorization: Optional[str] = Header(default=None), db=Depends(get_db)):
    unauthorized = HTTPException(401, "Your session has expired. Please log in again.")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorized
    try:
        payload = jwt.decode(authorization[7:].strip(), settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise unauthorized
    user = db.execute("SELECT * FROM users WHERE id = %s", (payload.get("sub"),)).fetchone()
    if not user or user["token_version"] != payload.get("tv"):
        raise unauthorized
    return user

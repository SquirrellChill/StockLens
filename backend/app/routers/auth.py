import base64
import io
import secrets
import time
import uuid
from typing import Optional

from psycopg.errors import UniqueViolation
from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Response, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel

from ..config import settings
from ..db import get_db
from ..emailer import send_reset_code
from ..security import (
    check_email, check_password, create_token, current_user, hash_code,
    hash_password, normalize_email, public_user, token_subject, verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Hash used to keep login timing similar when the email doesn't exist.
_DUMMY_HASH = hash_password("not-a-real-password")


class RegisterIn(BaseModel):
    full_name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class ProfileIn(BaseModel):
    full_name: str
    email: str


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    email: str
    code: str
    new_password: str


def _session(user) -> dict:
    return {"access_token": create_token(user), "token_type": "bearer", "user": public_user(user)}


@router.post("/register", status_code=201)
def register(body: RegisterIn, db=Depends(get_db)):
    name = body.full_name.strip()
    if not name:
        raise HTTPException(400, "Full name is required.")
    if len(name) > 100:
        raise HTTPException(400, "Full name is too long.")
    email = check_email(body.email)
    check_password(body.password)
    try:
        user = db.execute(
            "INSERT INTO users (id, name, email, password_hash) VALUES (%s,%s,%s,%s) RETURNING *",
            (str(uuid.uuid4()), name, email, hash_password(body.password)),
        ).fetchone()
    except UniqueViolation:
        raise HTTPException(409, "An account with this email already exists.")
    return _session(user)


@router.post("/login")
def login(body: LoginIn, db=Depends(get_db)):
    user = db.execute("SELECT * FROM users WHERE email = %s", (normalize_email(body.email),)).fetchone()
    ok = verify_password(body.password, user["password_hash"] if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(401, "Incorrect email or password.")
    return _session(user)


@router.get("/me")
def me(user=Depends(current_user)):
    return public_user(user)


@router.post("/logout", status_code=204)
def logout(_user=Depends(current_user)):
    # Tokens are stateless; the client discards its copy. (Changing the password revokes all tokens.)
    return Response(status_code=204)


@router.put("/profile")
def update_profile(body: ProfileIn, user=Depends(current_user), db=Depends(get_db)):
    name = body.full_name.strip()
    if not name:
        raise HTTPException(400, "Full name is required.")
    if len(name) > 100:
        raise HTTPException(400, "Full name is too long.")
    email = check_email(body.email)
    try:
        row = db.execute("UPDATE users SET name = %s, email = %s WHERE id = %s RETURNING *", (name, email, user["id"])).fetchone()
    except UniqueViolation:
        raise HTTPException(409, "Another account already uses this email.")
    return {"user": public_user(row)}


@router.post("/avatar")
def upload_avatar(file: UploadFile = File(...), user=Depends(current_user), db=Depends(get_db)):
    raw = file.file.read(settings.max_upload_bytes + 1)
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(413, "That image is too large. Please choose one under 10 MB.")
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "We could not read that image. Try a different file.")
    img = ImageOps.fit(img, (256, 256))  # square crop, regardless of what the client sent
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    row = db.execute("UPDATE users SET avatar = %s WHERE id = %s RETURNING *", (data_url, user["id"])).fetchone()
    return {"user": public_user(row)}


@router.delete("/avatar", status_code=204)
def remove_avatar(user=Depends(current_user), db=Depends(get_db)):
    db.execute("UPDATE users SET avatar = NULL WHERE id = %s", (user["id"],))
    return Response(status_code=204)


@router.post("/forgot-password")
def forgot_password(body: ForgotIn, background: BackgroundTasks, db=Depends(get_db)):
    email = check_email(body.email)
    user = db.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()
    result: dict = {"ok": True}  # identical response whether or not the account exists
    if not user:
        return result
    code = str(secrets.randbelow(900000) + 100000)
    with db.transaction():
        db.execute("DELETE FROM resets WHERE user_id = %s OR expires_at < %s", (user["id"], time.time()))
        db.execute(
            "INSERT INTO resets (user_id, code_hash, expires_at) VALUES (%s,%s,%s)",
            (user["id"], hash_code(code), time.time() + settings.reset_ttl_minutes * 60),
        )
    background.add_task(send_reset_code, email, code)
    if settings.dev_expose_reset_code:
        result["demo_reset_code"] = code
    return result


@router.post("/reset-password")
def reset_password(body: ResetIn, authorization: Optional[str] = Header(default=None), db=Depends(get_db)):
    email = check_email(body.email)
    code = str(body.code or "").strip()
    if not (code.isdigit() and len(code) == 6):
        raise HTTPException(400, "Enter the 6-digit code we sent you.")
    check_password(body.new_password)
    invalid = HTTPException(400, "That code is invalid or has expired. Please request a new one.")

    user = db.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()
    if not user:
        raise invalid
    wrong_code = False
    with db.transaction():
        entry = db.execute(
            "SELECT * FROM resets WHERE user_id = %s AND expires_at > %s FOR UPDATE", (user["id"], time.time())
        ).fetchone()
        if not entry:
            raise invalid
        if not secrets.compare_digest(entry["code_hash"], hash_code(code)):
            wrong_code = True  # record the attempt, then fail after the transaction commits
            if entry["attempts"] + 1 >= settings.reset_max_attempts:
                db.execute("DELETE FROM resets WHERE id = %s", (entry["id"],))
            else:
                db.execute("UPDATE resets SET attempts = attempts + 1 WHERE id = %s", (entry["id"],))
        else:
            db.execute(
                "UPDATE users SET password_hash = %s, token_version = token_version + 1 WHERE id = %s",
                (hash_password(body.new_password), user["id"]),
            )
            db.execute("DELETE FROM resets WHERE user_id = %s", (user["id"],))
    if wrong_code:
        raise invalid
    result: dict = {"ok": True}
    # Changing the password signs out every device. If this request came from the signed-in owner
    # (Settings -> Change password), hand back a fresh token so *this* session keeps working.
    if token_subject(authorization) == user["id"]:
        fresh = db.execute("SELECT * FROM users WHERE id = %s", (user["id"],)).fetchone()
        result["access_token"] = create_token(fresh)
    return result

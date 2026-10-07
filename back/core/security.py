import secrets
import uuid
import jwt
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash

from core.config import settings


password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    return _encode({
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    })


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    jti = secrets.token_urlsafe(32)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token = _encode({
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": expires_at
    })
    return token, jti, expires_at


def decode_token(token: str, expected_type: str) -> dict:
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub", "type"]}
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Tipo de token inválido")
    return payload

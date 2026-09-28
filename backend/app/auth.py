import hashlib
import hmac
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .entities import AccessTokenRecord, StaffRecord
from .models import StaffUser
from .store import get_db, staff_to_api

TOKEN_TTL_SECONDS = 8 * 60 * 60
_Scrypt = dict(n=2**14, r=8, p=1)
bearer_scheme = HTTPBearer(auto_error=False, scheme_name="bearerAuth")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_Scrypt)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, salt_hex, expected_hex = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except (ValueError, TypeError):
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, dklen=len(expected), **_Scrypt)
    return hmac.compare_digest(actual, expected)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(db: Session, staff_id: str) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AccessTokenRecord(
        token_hash=token_digest(token),
        staff_id=staff_id,
        expires_at=int(time.time()) + TOKEN_TTL_SECONDS,
    ))
    db.commit()
    return token


def staff_for_token(db: Session, token: str | None) -> StaffUser | None:
    if not token:
        return None
    session = db.get(AccessTokenRecord, token_digest(token))
    if not session:
        return None
    if session.expires_at <= int(time.time()):
        return None
    account = db.get(StaffRecord, session.staff_id)
    return staff_to_api(account) if account else None


def optional_current_staff(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> StaffUser | None:
    token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
    return staff_for_token(db, token)


def require_current_staff(
    user: Annotated[StaffUser | None, Depends(optional_current_staff)],
) -> StaffUser:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentStaff = Annotated[StaffUser, Depends(require_current_staff)]

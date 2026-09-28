import hashlib
import hmac
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import StaffUser

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


def issue_token(request: Request, staff_id: str) -> str:
    token = secrets.token_urlsafe(32)
    request.app.state.store.sessions[token_digest(token)] = {
        "staff_id": staff_id,
        "expires_at": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    return token


def staff_for_token(request: Request, token: str | None) -> StaffUser | None:
    if not token:
        return None
    sessions = request.app.state.store.sessions
    session = sessions.get(token_digest(token))
    if not session:
        return None
    if session["expires_at"] <= int(time.time()):
        sessions.pop(token_digest(token), None)
        return None
    account = request.app.state.store.staff_by_id(session["staff_id"])
    return account.user if account else None


def optional_current_staff(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> StaffUser | None:
    token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
    return staff_for_token(request, token)


def require_current_staff(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> StaffUser:
    user = optional_current_staff(request, credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentStaff = Annotated[StaffUser, Depends(require_current_staff)]

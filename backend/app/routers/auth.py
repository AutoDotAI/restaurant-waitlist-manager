from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..auth import (
    CurrentStaff,
    TOKEN_TTL_SECONDS,
    bearer_scheme,
    issue_token,
    optional_current_staff,
    token_digest,
    verify_password,
)
from ..models import LoginInput, LoginResponse, StaffUser
from ..entities import AccessTokenRecord, StaffRecord
from ..store import get_db, staff_to_api

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/session", response_model=StaffUser | None)
def get_session(user: Annotated[StaffUser | None, Depends(optional_current_staff)]) -> StaffUser | None:
    return user


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginInput, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    account = db.scalar(select(StaffRecord).where(func.lower(StaffRecord.email) == str(payload.email).lower()))
    if account is None or not verify_password(payload.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = issue_token(db, account.id)
    return LoginResponse(
        accessToken=token,
        expiresIn=TOKEN_TTL_SECONDS,
        user=staff_to_api(account),
    )


@router.post("/logout")
def logout(
    user: CurrentStaff,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    del user
    if credentials:
        db.execute(delete(AccessTokenRecord).where(AccessTokenRecord.token_hash == token_digest(credentials.credentials)))
        db.commit()
    return {"success": True}

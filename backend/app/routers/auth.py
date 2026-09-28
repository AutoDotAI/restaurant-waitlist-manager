import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from ..auth import (
    CurrentStaff,
    TOKEN_TTL_SECONDS,
    bearer_scheme,
    hash_password,
    issue_token,
    optional_current_staff,
    token_digest,
    verify_password,
)
from ..models import LoginInput, LoginResponse, StaffUser

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/session", response_model=StaffUser | None)
def get_session(user: Annotated[StaffUser | None, Depends(optional_current_staff)]) -> StaffUser | None:
    return user


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginInput, request: Request) -> LoginResponse:
    account = request.app.state.store.staff_by_email(str(payload.email))
    if account is None or not verify_password(payload.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = issue_token(request, account.user.id)
    return LoginResponse(
        accessToken=token,
        expiresIn=TOKEN_TTL_SECONDS,
        user=account.user,
    )


@router.post("/logout")
def logout(
    request: Request,
    user: CurrentStaff,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, bool]:
    del user
    if credentials:
        request.app.state.store.sessions.pop(token_digest(credentials.credentials), None)
    return {"success": True}

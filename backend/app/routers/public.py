from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..entities import WaitlistEntryRecord
from ..models import (
    JoinInput,
    PublicRestaurantInfo,
    PublicWaitlistStatus,
    RemoteJoinInput,
    RemoteJoinResponse,
    WaitlistEntry,
)
from ..store import (
    DuplicateActiveEntryError,
    as_utc,
    create_waitlist_entry,
    entry_to_api,
    get_db,
    get_restaurant_record,
    set_entry_status,
)

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/restaurants/{slug}", response_model=PublicRestaurantInfo)
def get_public_restaurant(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
) -> PublicRestaurantInfo:
    restaurant = get_restaurant_record(db)
    if slug != restaurant.slug:
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    active_count = len(db.scalars(
        select(WaitlistEntryRecord.id).where(
            WaitlistEntryRecord.status.in_(("WAITING", "ARRIVED", "NOTIFIED", "CONFIRMED"))
        )
    ).all())
    wait_base = active_count * restaurant.base_wait_per_group_minutes
    return PublicRestaurantInfo(
        name=restaurant.name, slug=restaurant.slug,
        remoteJoinEnabled=restaurant.remote_join_enabled,
        maxPartySize=restaurant.max_party_size,
        estimatedWaitRange=(int(wait_base), round(wait_base * 1.4) + 5),
        partiesWaiting=active_count,
    )


@router.post(
    "/restaurants/{slug}/waitlist",
    response_model=RemoteJoinResponse,
    status_code=status.HTTP_201_CREATED,
)
def join_remotely(
    slug: str,
    payload: RemoteJoinInput,
    db: Annotated[Session, Depends(get_db)],
) -> RemoteJoinResponse:
    restaurant = get_restaurant_record(db)
    if slug != restaurant.slug:
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    if not restaurant.remote_join_enabled:
        raise HTTPException(status_code=409, detail="Remote joining is currently closed.")
    try:
        entry = create_waitlist_entry(
            db, restaurant, JoinInput(**payload.model_dump(), source="REMOTE")
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicateActiveEntryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RemoteJoinResponse(token=entry.public_token)


@router.get("/waitlist/{token}", response_model=PublicWaitlistStatus)
def get_public_status(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> PublicWaitlistStatus:
    entry = db.scalar(select(WaitlistEntryRecord).where(WaitlistEntryRecord.public_token == token))
    if entry is None:
        raise HTTPException(status_code=404, detail="This waitlist link is no longer valid.")
    restaurant = get_restaurant_record(db)
    displayed_wait = entry.manual_wait_override if entry.manual_wait_override is not None else entry.estimated_wait_minutes
    return PublicWaitlistStatus(
        restaurantName=restaurant.name, customerName=entry.customer_name,
        partySize=entry.party_size, status=entry.status,
        estimatedWaitMinutes=displayed_wait,
        gracePeriodMinutes=restaurant.grace_period_minutes,
        notifiedAt=as_utc(entry.notified_at),
    )


def _customer_action(token: str, db: Session, status_value: str) -> WaitlistEntry:
    entry = db.scalar(select(WaitlistEntryRecord).where(WaitlistEntryRecord.public_token == token))
    if entry is None:
        raise HTTPException(status_code=404, detail="This waitlist link is no longer valid.")
    set_entry_status(db, get_restaurant_record(db), entry, status_value)
    db.commit()
    db.refresh(entry)
    return entry_to_api(entry)


@router.post("/waitlist/{token}/confirm", response_model=WaitlistEntry)
def customer_confirm(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> WaitlistEntry:
    return _customer_action(token, db, "CONFIRMED")


@router.post("/waitlist/{token}/cancel", response_model=WaitlistEntry)
def customer_cancel(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> WaitlistEntry:
    return _customer_action(token, db, "CANCELLED")

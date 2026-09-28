from fastapi import APIRouter, HTTPException, Request, status

from ..models import (
    JoinInput,
    PublicRestaurantInfo,
    PublicWaitlistStatus,
    RemoteJoinInput,
    RemoteJoinResponse,
    WaitlistEntry,
)

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/restaurants/{slug}", response_model=PublicRestaurantInfo)
def get_public_restaurant(slug: str, request: Request) -> PublicRestaurantInfo:
    store = request.app.state.store
    if slug != store.restaurant.slug:
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    active_count = len(store.active_queue())
    base = active_count * store.restaurant.baseWaitPerGroupMinutes
    return PublicRestaurantInfo(
        name=store.restaurant.name, slug=store.restaurant.slug,
        remoteJoinEnabled=store.restaurant.remoteJoinEnabled,
        maxPartySize=store.restaurant.maxPartySize,
        estimatedWaitRange=(int(base), round(base * 1.4) + 5),
        partiesWaiting=active_count,
    )


@router.post(
    "/restaurants/{slug}/waitlist",
    response_model=RemoteJoinResponse,
    status_code=status.HTTP_201_CREATED,
)
def join_remotely(slug: str, payload: RemoteJoinInput, request: Request) -> RemoteJoinResponse:
    store = request.app.state.store
    if slug != store.restaurant.slug:
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    if not store.restaurant.remoteJoinEnabled:
        raise HTTPException(status_code=409, detail="Remote joining is currently closed.")
    try:
        entry = store.add_entry(JoinInput(**payload.model_dump(), source="REMOTE"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RemoteJoinResponse(token=entry.publicToken)


@router.get("/waitlist/{token}", response_model=PublicWaitlistStatus)
def get_public_status(token: str, request: Request) -> PublicWaitlistStatus:
    store = request.app.state.store
    entry = store.entry_by_token(token)
    if entry is None:
        raise HTTPException(status_code=404, detail="This waitlist link is no longer valid.")
    displayed_wait = entry.manualWaitOverride if entry.manualWaitOverride is not None else entry.estimatedWaitMinutes
    return PublicWaitlistStatus(
        restaurantName=store.restaurant.name, customerName=entry.customerName,
        partySize=entry.partySize, status=entry.status,
        estimatedWaitMinutes=displayed_wait,
        gracePeriodMinutes=store.restaurant.gracePeriodMinutes,
        notifiedAt=entry.notifiedAt,
    )


def _customer_action(token: str, request: Request, status_value: str) -> WaitlistEntry:
    store = request.app.state.store
    entry = store.entry_by_token(token)
    if entry is None:
        raise HTTPException(status_code=404, detail="This waitlist link is no longer valid.")
    return store.set_status(entry, status_value)


@router.post("/waitlist/{token}/confirm", response_model=WaitlistEntry)
def customer_confirm(token: str, request: Request) -> WaitlistEntry:
    return _customer_action(token, request, "CONFIRMED")


@router.post("/waitlist/{token}/cancel", response_model=WaitlistEntry)
def customer_cancel(token: str, request: Request) -> WaitlistEntry:
    return _customer_action(token, request, "CANCELLED")

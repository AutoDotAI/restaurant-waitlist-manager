from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from ..auth import CurrentStaff
from ..models import (
    AnalyticsSummary,
    JoinInput,
    ReorderInput,
    SmsMessage,
    StatusInput,
    WaitlistEntry,
    WaitlistEntryPatch,
)
from ..store import ACTIVE_STATUSES

router = APIRouter(tags=["Waitlist", "Analytics"])


@router.get("/waitlist", response_model=list[WaitlistEntry])
def list_queue(request: Request, user: CurrentStaff) -> list[WaitlistEntry]:
    del user
    return request.app.state.store.active_queue()


@router.post("/waitlist", response_model=WaitlistEntry, status_code=201)
def add_guest(payload: JoinInput, request: Request, user: CurrentStaff) -> WaitlistEntry:
    del user
    try:
        return request.app.state.store.add_entry(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/waitlist/history", response_model=list[WaitlistEntry])
def list_history(request: Request, user: CurrentStaff) -> list[WaitlistEntry]:
    del user
    return request.app.state.store.history()


@router.put("/waitlist/reorder", response_model=list[WaitlistEntry])
def reorder_queue(payload: ReorderInput, request: Request, user: CurrentStaff) -> list[WaitlistEntry]:
    del user
    store = request.app.state.store
    active_queue = store.active_queue()
    active_ids = {entry.id for entry in active_queue}
    if len(payload.orderedIds) != len(set(payload.orderedIds)) or set(payload.orderedIds) != active_ids:
        raise HTTPException(status_code=422, detail="orderedIds must include every active entry exactly once.")
    for position, entry_id in enumerate(payload.orderedIds, start=1):
        store.entries[entry_id].queuePosition = position
    return store.active_queue()


@router.patch("/waitlist/{entryId}", response_model=WaitlistEntry)
def update_guest(entryId: str, payload: WaitlistEntryPatch, request: Request, user: CurrentStaff) -> WaitlistEntry:
    del user
    store = request.app.state.store
    entry = store.entry(entryId)
    if entry is None:
        raise HTTPException(status_code=404, detail="Guest not found.")
    updated = entry.model_copy(update=payload.model_dump(exclude_unset=True))
    store.entries[entryId] = updated
    store.recalculate()
    return updated


@router.put("/waitlist/{entryId}/status", response_model=WaitlistEntry)
def set_guest_status(entryId: str, payload: StatusInput, request: Request, user: CurrentStaff) -> WaitlistEntry:
    del user
    store = request.app.state.store
    entry = store.entry(entryId)
    if entry is None:
        raise HTTPException(status_code=404, detail="Guest not found.")
    return store.set_status(entry, payload.status)


@router.get("/waitlist/sms", response_model=list[SmsMessage])
def list_sms(request: Request, user: CurrentStaff) -> list[SmsMessage]:
    del user
    return request.app.state.store.sms[:30]


@router.get("/analytics", response_model=AnalyticsSummary)
def get_analytics(
    request: Request,
    user: CurrentStaff,
    range: Literal["today", "7d", "30d"] = Query(...),
) -> AnalyticsSummary:
    del user
    store = request.app.state.store
    day_count = {"today": 1, "7d": 7, "30d": 30}[range]
    since = datetime.now(timezone.utc) - timedelta(days=day_count)
    rows = [entry for entry in store.entries.values() if entry.joinedAt >= since]
    seated = [entry for entry in rows if entry.status == "SEATED"]
    actual_waits = [
        (entry.seatedAt - entry.joinedAt).total_seconds() / 60
        for entry in seated if entry.seatedAt is not None
    ]

    def average(values: list[float]) -> float:
        return round(sum(values) / len(values)) if values else 0

    estimate_values = [
        float(entry.manualWaitOverride if entry.manualWaitOverride is not None else entry.estimatedWaitMinutes)
        for entry in rows
    ]
    average_party = average([float(entry.partySize) for entry in rows])
    return AnalyticsSummary(
        guestsServed=len(seated),
        averageEstimatedWait=average(estimate_values),
        averageActualWait=average(actual_waits),
        cancellations=sum(entry.status == "CANCELLED" for entry in rows),
        noShows=sum(entry.status == "NO_SHOW" for entry in rows),
        walkIns=sum(entry.source == "WALK_IN" for entry in rows),
        remoteJoins=sum(entry.source == "REMOTE" for entry in rows),
        averagePartySize=round(average_party * 10) / 10 if rows else 0,
    )

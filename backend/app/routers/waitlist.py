from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import CurrentStaff
from ..entities import SmsRecord, WaitlistEntryRecord
from ..models import (
    AnalyticsSummary,
    JoinInput,
    ReorderInput,
    SmsMessage,
    StatusInput,
    WaitlistEntry,
    WaitlistEntryPatch,
)
from ..store import (
    ACTIVE_STATUSES,
    DuplicateActiveEntryError,
    as_utc,
    create_waitlist_entry,
    entry_to_api,
    get_db,
    get_restaurant_record,
    recalculate_queue,
    set_entry_status,
    sms_to_api,
)

router = APIRouter(tags=["Waitlist", "Analytics"])


@router.get("/waitlist", response_model=list[WaitlistEntry])
def list_queue(
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> list[WaitlistEntry]:
    del user
    rows = recalculate_queue(db, get_restaurant_record(db))
    db.commit()
    return [entry_to_api(row) for row in rows]


@router.post("/waitlist", response_model=WaitlistEntry, status_code=201)
def add_guest(
    payload: JoinInput,
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> WaitlistEntry:
    del user
    try:
        row = create_waitlist_entry(db, get_restaurant_record(db), payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicateActiveEntryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return entry_to_api(row)


@router.get("/waitlist/history", response_model=list[WaitlistEntry])
def list_history(
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> list[WaitlistEntry]:
    del user
    rows = db.scalars(
        select(WaitlistEntryRecord)
        .where(WaitlistEntryRecord.status.not_in(ACTIVE_STATUSES))
        .order_by(WaitlistEntryRecord.joined_at.desc())
    ).all()
    return [entry_to_api(row) for row in rows]


@router.put("/waitlist/reorder", response_model=list[WaitlistEntry])
def reorder_queue(
    payload: ReorderInput,
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> list[WaitlistEntry]:
    del user
    restaurant = get_restaurant_record(db)
    current = recalculate_queue(db, restaurant)
    active_ids = {entry.id for entry in current}
    if len(payload.orderedIds) != len(set(payload.orderedIds)) or set(payload.orderedIds) != active_ids:
        raise HTTPException(status_code=422, detail="orderedIds must include every active entry exactly once.")
    by_id = {entry.id: entry for entry in current}
    for position, entry_id in enumerate(payload.orderedIds, start=1):
        by_id[entry_id].queue_position = position
    db.flush()
    ordered = recalculate_queue(db, restaurant)
    db.commit()
    return [entry_to_api(entry) for entry in ordered]


@router.patch("/waitlist/{entryId}", response_model=WaitlistEntry)
def update_guest(
    entryId: str,
    payload: WaitlistEntryPatch,
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> WaitlistEntry:
    del user
    entry = db.get(WaitlistEntryRecord, entryId)
    if entry is None:
        raise HTTPException(status_code=404, detail="Guest not found.")
    fields = {
        "customerName": "customer_name",
        "phoneNumber": "phone_number",
        "partySize": "party_size",
        "source": "source",
        "status": "status",
        "estimatedWaitMinutes": "estimated_wait_minutes",
        "manualWaitOverride": "manual_wait_override",
        "queuePosition": "queue_position",
        "expectedArrivalAt": "expected_arrival_at",
        "arrivedAt": "arrived_at",
        "notifiedAt": "notified_at",
        "confirmedAt": "confirmed_at",
        "seatedAt": "seated_at",
        "cancelledAt": "cancelled_at",
        "staffNotes": "staff_notes",
    }
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field.endswith("At") and value is not None:
            value = as_utc(value)
        setattr(entry, fields[field], value)
    db.flush()
    recalculate_queue(db, get_restaurant_record(db))
    db.commit()
    db.refresh(entry)
    return entry_to_api(entry)


@router.put("/waitlist/{entryId}/status", response_model=WaitlistEntry)
def set_guest_status(
    entryId: str,
    payload: StatusInput,
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> WaitlistEntry:
    del user
    entry = db.get(WaitlistEntryRecord, entryId)
    if entry is None:
        raise HTTPException(status_code=404, detail="Guest not found.")
    updated = set_entry_status(db, get_restaurant_record(db), entry, payload.status)
    db.commit()
    db.refresh(updated)
    return entry_to_api(updated)


@router.get("/waitlist/sms", response_model=list[SmsMessage])
def list_sms(
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> list[SmsMessage]:
    del user
    records = db.scalars(select(SmsRecord).order_by(SmsRecord.sent_at.desc()).limit(30)).all()
    return [sms_to_api(record) for record in records]


@router.get("/analytics", response_model=AnalyticsSummary)
def get_analytics(
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
    range: Literal["today", "7d", "30d"] = Query(...),
) -> AnalyticsSummary:
    del user
    days = {"today": 1, "7d": 7, "30d": 30}[range]
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.scalars(
        select(WaitlistEntryRecord).where(WaitlistEntryRecord.joined_at >= since)
    ).all()
    seated = [entry for entry in rows if entry.status == "SEATED"]
    actual_waits = [
        (as_utc(entry.seated_at) - as_utc(entry.joined_at)).total_seconds() / 60
        for entry in seated if entry.seated_at is not None
    ]

    def average(values: list[float]) -> float:
        return round(sum(values) / len(values)) if values else 0

    estimated_waits = [
        float(entry.manual_wait_override if entry.manual_wait_override is not None else entry.estimated_wait_minutes)
        for entry in rows
    ]
    avg_party_size = average([float(entry.party_size) for entry in rows])
    return AnalyticsSummary(
        guestsServed=len(seated),
        averageEstimatedWait=average(estimated_waits),
        averageActualWait=average(actual_waits),
        cancellations=sum(entry.status == "CANCELLED" for entry in rows),
        noShows=sum(entry.status == "NO_SHOW" for entry in rows),
        walkIns=sum(entry.source == "WALK_IN" for entry in rows),
        remoteJoins=sum(entry.source == "REMOTE" for entry in rows),
        averagePartySize=round(avg_party_size * 10) / 10 if rows else 0,
    )

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .entities import (
    Base,
    RestaurantRecord,
    SmsRecord,
    StaffRecord,
    WaitlistEntryRecord,
)
from .models import GuestStatus, JoinInput, Restaurant, SmsMessage, StaffUser, WaitlistEntry

ACTIVE_STATUSES = {"WAITING", "ARRIVED", "NOTIFIED", "CONFIRMED"}
DEFAULT_DATABASE_URL = "sqlite:///./waitlist.db"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_database_engine(database_url: str):
    """Create an engine from any SQLAlchemy URL, adding only SQLite-specific options when needed."""
    url = make_url(database_url)
    options: dict[str, Any] = {"pool_pre_ping": True}
    if url.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False}
        if url.database in (None, "", ":memory:"):
            options["poolclass"] = StaticPool

    engine = create_engine(url, **options)
    if url.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine):
    return sessionmaker(bind=engine, class_=Session, autoflush=False, expire_on_commit=False)


def get_db(request: Request):
    session_factory = request.app.state.session_factory
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(5)}"


def new_public_token() -> str:
    return secrets.token_urlsafe(18)


class DuplicateActiveEntryError(Exception):
    pass


def get_restaurant_record(db: Session) -> RestaurantRecord:
    record = db.scalar(select(RestaurantRecord).order_by(RestaurantRecord.id).limit(1))
    if record is None:
        raise LookupError("Restaurant not found.")
    return record


def create_waitlist_entry(
    db: Session,
    restaurant: RestaurantRecord,
    payload: JoinInput,
) -> WaitlistEntryRecord:
    if payload.partySize > restaurant.max_party_size:
        raise ValueError(f"Maximum party size is {restaurant.max_party_size}.")
    phone = "".join(payload.phoneNumber.split())
    active_entries = db.scalars(
        select(WaitlistEntryRecord).where(WaitlistEntryRecord.status.in_(ACTIVE_STATUSES))
    ).all()
    if any("".join(entry.phone_number.split()) == phone for entry in active_entries):
        raise DuplicateActiveEntryError("This phone number already has an active waitlist entry.")

    joined_at = utc_now()
    position = len(active_entries) + 1
    entry = WaitlistEntryRecord(
        id=new_id("wl"), restaurant_id=restaurant.id, public_token=new_public_token(),
        customer_name=payload.customerName, phone_number=payload.phoneNumber,
        party_size=payload.partySize, source=payload.source, status="WAITING",
        estimated_wait_minutes=0, manual_wait_override=None, queue_position=position,
        joined_at=joined_at,
        expected_arrival_at=joined_at + timedelta(minutes=restaurant.arrival_window_minutes) if payload.source == "REMOTE" else None,
        arrived_at=None, notified_at=None, confirmed_at=None, seated_at=None,
        cancelled_at=None, staff_notes=getattr(payload, "staffNotes", ""),
    )
    db.add(entry)
    db.flush()
    recalculate_queue(db, restaurant)
    send_sms(db, restaurant, entry, "WAITLIST_CONFIRMATION")
    db.commit()
    db.refresh(entry)
    return entry


def initialize_database(engine, session_factory) -> None:
    Base.metadata.create_all(engine)
    with session_factory() as db:
        if db.scalar(select(RestaurantRecord.id).limit(1)) is not None:
            return
        seed_database(db)


def seed_database(db: Session) -> None:
    # Import here to keep persistence setup independent from the auth dependency module.
    from .auth import hash_password

    restaurant = RestaurantRecord(
        id="rest_1", slug="big-mamma", name="Ober Mamma", timezone="Europe/Paris",
        phone_country_code="+33", remote_join_enabled=True, arrival_window_minutes=30,
        grace_period_minutes=10, max_party_size=12, base_wait_per_group_minutes=7,
        sms_sender_name="OberMamma",
    )
    db.add(restaurant)
    staff_users = [
        StaffRecord(
            id="staff_1", restaurant_id=restaurant.id, name="Claire Dubois",
            email="claire@obermamma.fr", role="MANAGER", password_hash=hash_password("demo-password"),
        ),
        StaffRecord(
            id="staff_2", restaurant_id=restaurant.id, name="Tom Réno",
            email="tom@obermamma.fr", role="HOST", password_hash=hash_password("demo-password"),
        ),
    ]
    db.add_all(staff_users)

    active = [
        ("Sarah", "+33 6 12 34 56 78", 2, "WALK_IN", "WAITING", 12),
        ("Julien", "+33 6 22 41 09 13", 4, "REMOTE", "ARRIVED", 22),
        ("Emma", "+33 6 87 55 20 44", 3, "REMOTE", "NOTIFIED", 31),
        ("David", "+33 6 71 08 66 90", 2, "WALK_IN", "WAITING", 4),
        ("Léa", "+33 6 45 77 31 02", 6, "REMOTE", "WAITING", 2),
    ]
    timestamp = utc_now()
    for position, (name, phone, party, source, status, age) in enumerate(active, start=1):
        joined = timestamp - timedelta(minutes=age)
        db.add(WaitlistEntryRecord(
            id=new_id("wl"), restaurant_id=restaurant.id, public_token=new_public_token(),
            customer_name=name, phone_number=phone, party_size=party, source=source,
            status=status, estimated_wait_minutes=0, manual_wait_override=None,
            queue_position=position, joined_at=joined,
            expected_arrival_at=joined + timedelta(minutes=restaurant.arrival_window_minutes) if source == "REMOTE" else None,
            arrived_at=timestamp if status == "ARRIVED" else None,
            notified_at=timestamp if status == "NOTIFIED" else None,
            confirmed_at=None, seated_at=None, cancelled_at=None, staff_notes="",
        ))

    history = [
        ("Marco", 2, "SEATED", 95, "WALK_IN"),
        ("Inès", 4, "SEATED", 80, "REMOTE"),
        ("Paul", 5, "NO_SHOW", 70, "REMOTE"),
        ("Nora", 3, "SEATED", 60, "WALK_IN"),
        ("Hugo", 2, "CANCELLED", 50, "REMOTE"),
    ]
    for index, (name, party, status, age, source) in enumerate(history):
        joined = timestamp - timedelta(minutes=age)
        db.add(WaitlistEntryRecord(
            id=new_id("wl"), restaurant_id=restaurant.id, public_token=new_public_token(),
            customer_name=name, phone_number=f"+33 6 00 00 00 0{index}", party_size=party,
            source=source, status=status, estimated_wait_minutes=20, manual_wait_override=None,
            queue_position=100 + index, joined_at=joined, expected_arrival_at=None,
            arrived_at=None, notified_at=joined + timedelta(minutes=15), confirmed_at=None,
            seated_at=joined + timedelta(minutes=22) if status == "SEATED" else None,
            cancelled_at=joined + timedelta(minutes=10) if status == "CANCELLED" else None,
            staff_notes="",
        ))

    db.flush()
    recalculate_queue(db, restaurant)
    db.commit()


def recalculate_queue(db: Session, restaurant: RestaurantRecord) -> list[WaitlistEntryRecord]:
    entries = list(db.scalars(
        select(WaitlistEntryRecord)
        .where(WaitlistEntryRecord.status.in_(ACTIVE_STATUSES))
        .order_by(WaitlistEntryRecord.queue_position, WaitlistEntryRecord.joined_at)
    ))
    for position, entry in enumerate(entries):
        if entry.party_size <= 2:
            modifier = 1
        elif entry.party_size <= 4:
            modifier = 1.2
        elif entry.party_size <= 6:
            modifier = 1.5
        else:
            modifier = 2
        entry.queue_position = position + 1
        entry.estimated_wait_minutes = max(
            0,
            round(position * restaurant.base_wait_per_group_minutes * modifier),
        )
    return entries


def restaurant_to_api(record: RestaurantRecord) -> Restaurant:
    return Restaurant(
        id=record.id, slug=record.slug, name=record.name, timezone=record.timezone,
        phoneCountryCode=record.phone_country_code,
        remoteJoinEnabled=record.remote_join_enabled,
        arrivalWindowMinutes=record.arrival_window_minutes,
        gracePeriodMinutes=record.grace_period_minutes,
        maxPartySize=record.max_party_size,
        baseWaitPerGroupMinutes=record.base_wait_per_group_minutes,
        smsSenderName=record.sms_sender_name,
    )


def staff_to_api(record: StaffRecord) -> StaffUser:
    return StaffUser(
        id=record.id, restaurantId=record.restaurant_id, name=record.name,
        email=record.email, role=record.role,
    )


def entry_to_api(record: WaitlistEntryRecord) -> WaitlistEntry:
    return WaitlistEntry(
        id=record.id, restaurantId=record.restaurant_id, publicToken=record.public_token,
        customerName=record.customer_name, phoneNumber=record.phone_number,
        partySize=record.party_size, source=record.source, status=record.status,
        estimatedWaitMinutes=record.estimated_wait_minutes,
        manualWaitOverride=record.manual_wait_override, queuePosition=record.queue_position,
        joinedAt=as_utc(record.joined_at), expectedArrivalAt=as_utc(record.expected_arrival_at),
        arrivedAt=as_utc(record.arrived_at), notifiedAt=as_utc(record.notified_at),
        confirmedAt=as_utc(record.confirmed_at), seatedAt=as_utc(record.seated_at),
        cancelledAt=as_utc(record.cancelled_at), staffNotes=record.staff_notes,
    )


def sms_to_api(record: SmsRecord) -> SmsMessage:
    return SmsMessage(
        id=record.id, waitlistEntryId=record.waitlist_entry_id,
        phoneNumber=record.phone_number, messageType=record.message_type,
        body=record.body, status=record.status, sentAt=as_utc(record.sent_at),
    )


def send_sms(db: Session, restaurant: RestaurantRecord, entry: WaitlistEntryRecord, message_type: str) -> SmsRecord:
    wait = entry.manual_wait_override if entry.manual_wait_override is not None else entry.estimated_wait_minutes
    link = f"/r/status/{entry.public_token}"
    body = {
        "WAITLIST_CONFIRMATION": f"You're on the waitlist at {restaurant.name}. Estimated wait: ~{wait} minutes. Track your wait: {link}",
        "TABLE_NEARLY_READY": f"Your table at {restaurant.name} is nearly ready. Please confirm you're coming: {link}",
        "CONFIRMATION_RECEIVED": f"Thanks — we've confirmed you're coming. Please head to {restaurant.name}.",
    }[message_type]
    record = SmsRecord(
        id=new_id("sms"), waitlist_entry_id=entry.id, phone_number=entry.phone_number,
        message_type=message_type, body=body, status="SENT", sent_at=utc_now(),
    )
    db.add(record)
    return record


def set_entry_status(
    db: Session,
    restaurant: RestaurantRecord,
    entry: WaitlistEntryRecord,
    new_status: GuestStatus,
) -> WaitlistEntryRecord:
    entry.status = new_status
    timestamp = utc_now()
    if new_status == "ARRIVED":
        entry.arrived_at = timestamp
    elif new_status == "NOTIFIED":
        entry.notified_at = timestamp
        send_sms(db, restaurant, entry, "TABLE_NEARLY_READY")
    elif new_status == "CONFIRMED":
        entry.confirmed_at = timestamp
        send_sms(db, restaurant, entry, "CONFIRMATION_RECEIVED")
    elif new_status == "SEATED":
        entry.seated_at = timestamp
    elif new_status == "CANCELLED":
        entry.cancelled_at = timestamp
    db.flush()
    recalculate_queue(db, restaurant)
    return entry

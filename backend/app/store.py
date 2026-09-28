import secrets
from datetime import datetime, timedelta, timezone

from .auth import hash_password
from .models import (
    GuestStatus,
    JoinInput,
    Restaurant,
    SmsMessage,
    StaffAccount,
    StaffUser,
    WaitlistEntry,
)

ACTIVE_STATUSES = {"WAITING", "ARRIVED", "NOTIFIED", "CONFIRMED"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryStore:
    """Replaceable in-memory persistence adapter used by the mock backend."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.restaurant = Restaurant(
            id="rest_1", slug="big-mamma", name="Ober Mamma", timezone="Europe/Paris",
            phoneCountryCode="+33", remoteJoinEnabled=True, arrivalWindowMinutes=30,
            gracePeriodMinutes=10, maxPartySize=12, baseWaitPerGroupMinutes=7,
            smsSenderName="OberMamma",
        )
        self.staff: dict[str, StaffAccount] = {}
        self.entries: dict[str, WaitlistEntry] = {}
        self.sms: list[SmsMessage] = []
        self.sessions: dict[str, dict[str, int | str]] = {}
        self._seed_staff()
        self._seed_entries()
        self.recalculate()

    @staticmethod
    def new_id(prefix: str) -> str:
        return f"{prefix}_{secrets.token_hex(5)}"

    @staticmethod
    def new_public_token() -> str:
        return secrets.token_urlsafe(18)

    def _seed_staff(self) -> None:
        # Demo logins: claire@obermamma.fr and tom@obermamma.fr / demo-password
        users = [
            StaffUser(id="staff_1", restaurantId="rest_1", name="Claire Dubois", email="claire@obermamma.fr", role="MANAGER"),
            StaffUser(id="staff_2", restaurantId="rest_1", name="Tom Réno", email="tom@obermamma.fr", role="HOST"),
        ]
        for user in users:
            self.staff[user.id] = StaffAccount(user, hash_password("demo-password"))

    def _make_entry(
        self,
        name: str,
        phone: str,
        party_size: int,
        source: str,
        status: str,
        joined_at: datetime,
        *,
        staff_notes: str = "",
        arrived_at: datetime | None = None,
        notified_at: datetime | None = None,
        seated_at: datetime | None = None,
        cancelled_at: datetime | None = None,
    ) -> WaitlistEntry:
        entry = WaitlistEntry(
            id=self.new_id("wl"), restaurantId=self.restaurant.id,
            publicToken=self.new_public_token(), customerName=name, phoneNumber=phone,
            partySize=party_size, source=source, status=status,
            estimatedWaitMinutes=20 if status not in ACTIVE_STATUSES else 0,
            manualWaitOverride=None, queuePosition=len(self.entries) + 1, joinedAt=joined_at,
            expectedArrivalAt=(joined_at + timedelta(minutes=self.restaurant.arrivalWindowMinutes)) if source == "REMOTE" and status in ACTIVE_STATUSES else None,
            arrivedAt=arrived_at, notifiedAt=notified_at, confirmedAt=None, seatedAt=seated_at,
            cancelledAt=cancelled_at, staffNotes=staff_notes,
        )
        self.entries[entry.id] = entry
        return entry

    def _seed_entries(self) -> None:
        active = [
            ("Sarah", "+33 6 12 34 56 78", 2, "WALK_IN", "WAITING", 12),
            ("Julien", "+33 6 22 41 09 13", 4, "REMOTE", "ARRIVED", 22),
            ("Emma", "+33 6 87 55 20 44", 3, "REMOTE", "NOTIFIED", 31),
            ("David", "+33 6 71 08 66 90", 2, "WALK_IN", "WAITING", 4),
            ("Léa", "+33 6 45 77 31 02", 6, "REMOTE", "WAITING", 2),
        ]
        for name, phone, party, source, entry_status, age in active:
            joined = utc_now() - timedelta(minutes=age)
            self._make_entry(
                name, phone, party, source, entry_status, joined,
                arrived_at=utc_now() if entry_status == "ARRIVED" else None,
                notified_at=utc_now() if entry_status == "NOTIFIED" else None,
            )
        history = [
            ("Marco", 2, "SEATED", 95, "WALK_IN"),
            ("Inès", 4, "SEATED", 80, "REMOTE"),
            ("Paul", 5, "NO_SHOW", 70, "REMOTE"),
            ("Nora", 3, "SEATED", 60, "WALK_IN"),
            ("Hugo", 2, "CANCELLED", 50, "REMOTE"),
        ]
        for i, (name, party, entry_status, age, source) in enumerate(history):
            joined = utc_now() - timedelta(minutes=age)
            self._make_entry(
                name, f"+33 6 00 00 00 0{i}", party, source, entry_status, joined,
                notified_at=joined + timedelta(minutes=15),
                seated_at=joined + timedelta(minutes=22) if entry_status == "SEATED" else None,
                cancelled_at=joined + timedelta(minutes=10) if entry_status == "CANCELLED" else None,
            )

    def staff_by_email(self, email: str) -> StaffAccount | None:
        normalized = email.strip().lower()
        return next((account for account in self.staff.values() if account.user.email.lower() == normalized), None)

    def staff_by_id(self, staff_id: str) -> StaffAccount | None:
        return self.staff.get(staff_id)

    def add_staff(self, user: StaffUser, password_hash: str | None) -> None:
        self.staff[user.id] = StaffAccount(user, password_hash)

    def remove_staff(self, staff_id: str) -> None:
        self.staff.pop(staff_id, None)
        self.sessions = {
            key: session for key, session in self.sessions.items()
            if session.get("staff_id") != staff_id
        }

    def entry(self, entry_id: str) -> WaitlistEntry | None:
        return self.entries.get(entry_id)

    def entry_by_token(self, token: str) -> WaitlistEntry | None:
        return next((entry for entry in self.entries.values() if secrets.compare_digest(entry.publicToken, token)), None)

    def active_queue(self) -> list[WaitlistEntry]:
        self.recalculate()
        return sorted((entry for entry in self.entries.values() if entry.status in ACTIVE_STATUSES), key=lambda entry: entry.queuePosition)

    def history(self) -> list[WaitlistEntry]:
        return [entry for entry in self.entries.values() if entry.status not in ACTIVE_STATUSES]

    def recalculate(self) -> None:
        entries = sorted(
            (entry for entry in self.entries.values() if entry.status in ACTIVE_STATUSES),
            key=lambda entry: entry.queuePosition,
        )
        for position, entry in enumerate(entries):
            modifier = 1 if entry.partySize <= 2 else 1.2 if entry.partySize <= 4 else 1.5 if entry.partySize <= 6 else 2
            entry.queuePosition = position + 1
            entry.estimatedWaitMinutes = max(0, round(position * self.restaurant.baseWaitPerGroupMinutes * modifier))

    def send_sms(self, entry: WaitlistEntry, message_type: str) -> None:
        wait = entry.manualWaitOverride if entry.manualWaitOverride is not None else entry.estimatedWaitMinutes
        tracking_link = f"/r/status/{entry.publicToken}"
        body = {
            "WAITLIST_CONFIRMATION": f"You're on the waitlist at {self.restaurant.name}. Estimated wait: ~{wait} minutes. Track your wait: {tracking_link}",
            "TABLE_NEARLY_READY": f"Your table at {self.restaurant.name} is nearly ready. Please confirm you're coming: {tracking_link}",
            "CONFIRMATION_RECEIVED": f"Thanks — we've confirmed you're coming. Please head to {self.restaurant.name}.",
        }[message_type]
        message = SmsMessage(
            id=self.new_id("sms"), waitlistEntryId=entry.id, phoneNumber=entry.phoneNumber,
            messageType=message_type, body=body, status="SENT", sentAt=utc_now(),
        )
        self.sms.insert(0, message)

    def add_entry(self, payload: JoinInput) -> WaitlistEntry:
        if payload.partySize > self.restaurant.maxPartySize:
            raise ValueError(f"Maximum party size is {self.restaurant.maxPartySize}.")
        normalized_phone = "".join(payload.phoneNumber.split())
        duplicate = any(
            entry.status in ACTIVE_STATUSES
            and "".join(entry.phoneNumber.split()) == normalized_phone
            for entry in self.entries.values()
        )
        if duplicate:
            raise RuntimeError("This phone number already has an active waitlist entry.")
        joined_at = utc_now()
        entry = WaitlistEntry(
            id=self.new_id("wl"), restaurantId=self.restaurant.id,
            publicToken=self.new_public_token(), customerName=payload.customerName,
            phoneNumber=payload.phoneNumber, partySize=payload.partySize, source=payload.source,
            status="WAITING", estimatedWaitMinutes=0, manualWaitOverride=None,
            queuePosition=len(self.entries) + 1, joinedAt=joined_at,
            expectedArrivalAt=(joined_at + timedelta(minutes=self.restaurant.arrivalWindowMinutes)) if payload.source == "REMOTE" else None,
            arrivedAt=None, notifiedAt=None, confirmedAt=None, seatedAt=None, cancelledAt=None,
            staffNotes=payload.staffNotes,
        )
        self.entries[entry.id] = entry
        self.recalculate()
        self.send_sms(entry, "WAITLIST_CONFIRMATION")
        return entry

    def set_status(self, entry: WaitlistEntry, status: GuestStatus) -> WaitlistEntry:
        entry.status = status
        stamp = utc_now()
        if status == "ARRIVED":
            entry.arrivedAt = stamp
        elif status == "NOTIFIED":
            entry.notifiedAt = stamp
            self.send_sms(entry, "TABLE_NEARLY_READY")
        elif status == "CONFIRMED":
            entry.confirmedAt = stamp
            self.send_sms(entry, "CONFIRMATION_RECEIVED")
        elif status == "SEATED":
            entry.seatedAt = stamp
        elif status == "CANCELLED":
            entry.cancelledAt = stamp
        self.recalculate()
        return entry


store = InMemoryStore()


def reset_store() -> None:
    store.reset()

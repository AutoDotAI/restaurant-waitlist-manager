from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

GuestStatus = Literal[
    "WAITING", "ARRIVED", "NOTIFIED", "CONFIRMED", "SEATED", "CANCELLED", "NO_SHOW", "REMOVED"
]
GuestSource = Literal["WALK_IN", "REMOTE"]
StaffRole = Literal["MANAGER", "HOST"]
SmsType = Literal["WAITLIST_CONFIRMATION", "TABLE_NEARLY_READY", "CONFIRMATION_RECEIVED"]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Restaurant(ApiModel):
    id: str
    slug: str
    name: str
    timezone: str
    phoneCountryCode: str
    remoteJoinEnabled: bool
    arrivalWindowMinutes: int = Field(ge=0)
    gracePeriodMinutes: int = Field(ge=0)
    maxPartySize: int = Field(ge=1)
    baseWaitPerGroupMinutes: float = Field(ge=0)
    smsSenderName: str


class RestaurantPatch(ApiModel):
    slug: str | None = None
    name: str | None = None
    timezone: str | None = None
    phoneCountryCode: str | None = None
    remoteJoinEnabled: bool | None = None
    arrivalWindowMinutes: int | None = Field(default=None, ge=0)
    gracePeriodMinutes: int | None = Field(default=None, ge=0)
    maxPartySize: int | None = Field(default=None, ge=1)
    baseWaitPerGroupMinutes: float | None = Field(default=None, ge=0)
    smsSenderName: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_values(cls, values):
        if isinstance(values, dict) and any(value is None for value in values.values()):
            raise ValueError("Restaurant settings cannot be null.")
        return values


class StaffUser(ApiModel):
    id: str
    restaurantId: str
    name: str
    email: EmailStr
    role: StaffRole


class LoginInput(ApiModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(ApiModel):
    accessToken: str
    tokenType: Literal["bearer"] = "bearer"
    expiresIn: int
    user: StaffUser


class RemoteJoinResponse(ApiModel):
    token: str


class NewStaff(ApiModel):
    name: str = Field(min_length=1)
    email: EmailStr
    role: StaffRole
    password: str | None = Field(default=None, min_length=12)


class JoinInput(ApiModel):
    customerName: str = Field(min_length=1)
    phoneNumber: str = Field(min_length=3)
    partySize: int = Field(ge=1)
    source: GuestSource
    staffNotes: str = ""


class RemoteJoinInput(ApiModel):
    customerName: str = Field(min_length=1)
    phoneNumber: str = Field(min_length=3)
    partySize: int = Field(ge=1)


class WaitlistEntry(ApiModel):
    id: str
    restaurantId: str
    publicToken: str
    customerName: str
    phoneNumber: str
    partySize: int
    source: GuestSource
    status: GuestStatus
    estimatedWaitMinutes: int
    manualWaitOverride: int | None
    queuePosition: int
    joinedAt: datetime
    expectedArrivalAt: datetime | None
    arrivedAt: datetime | None
    notifiedAt: datetime | None
    confirmedAt: datetime | None
    seatedAt: datetime | None
    cancelledAt: datetime | None
    staffNotes: str


class WaitlistEntryPatch(ApiModel):
    customerName: str | None = Field(default=None, min_length=1)
    phoneNumber: str | None = Field(default=None, min_length=3)
    partySize: int | None = Field(default=None, ge=1)
    source: GuestSource | None = None
    status: GuestStatus | None = None
    estimatedWaitMinutes: int | None = Field(default=None, ge=0)
    manualWaitOverride: int | None = Field(default=None, ge=0)
    queuePosition: int | None = Field(default=None, ge=1)
    expectedArrivalAt: datetime | None = None
    arrivedAt: datetime | None = None
    notifiedAt: datetime | None = None
    confirmedAt: datetime | None = None
    seatedAt: datetime | None = None
    cancelledAt: datetime | None = None
    staffNotes: str | None = None


class StatusInput(ApiModel):
    status: GuestStatus


class ReorderInput(ApiModel):
    orderedIds: list[str]


class SmsMessage(ApiModel):
    id: str
    waitlistEntryId: str
    phoneNumber: str
    messageType: SmsType
    body: str
    status: Literal["SENT", "FAILED"]
    sentAt: datetime


class PublicRestaurantInfo(ApiModel):
    name: str
    slug: str
    remoteJoinEnabled: bool
    maxPartySize: int
    estimatedWaitRange: tuple[int, int]
    partiesWaiting: int


class PublicWaitlistStatus(ApiModel):
    restaurantName: str
    customerName: str
    partySize: int
    status: GuestStatus
    estimatedWaitMinutes: int
    gracePeriodMinutes: int
    notifiedAt: datetime | None


class AnalyticsSummary(ApiModel):
    guestsServed: int
    averageEstimatedWait: float
    averageActualWait: float
    cancellations: int
    noShows: int
    walkIns: int
    remoteJoins: int
    averagePartySize: float

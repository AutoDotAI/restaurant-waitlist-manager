from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RestaurantRecord(Base):
    __tablename__ = "restaurants"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(100))
    phone_country_code: Mapped[str] = mapped_column(String(8))
    remote_join_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    arrival_window_minutes: Mapped[int] = mapped_column(Integer)
    grace_period_minutes: Mapped[int] = mapped_column(Integer)
    max_party_size: Mapped[int] = mapped_column(Integer)
    base_wait_per_group_minutes: Mapped[float] = mapped_column(Float)
    sms_sender_name: Mapped[str] = mapped_column(String(40))


class StaffRecord(Base):
    __tablename__ = "staff_users"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(ForeignKey("restaurants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)


class WaitlistEntryRecord(Base):
    __tablename__ = "waitlist_entries"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(ForeignKey("restaurants.id", ondelete="CASCADE"), index=True)
    public_token: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(200))
    phone_number: Mapped[str] = mapped_column(String(40))
    party_size: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), index=True)
    estimated_wait_minutes: Mapped[int] = mapped_column(Integer, default=0)
    manual_wait_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queue_position: Mapped[int] = mapped_column(Integer, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expected_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    staff_notes: Mapped[str] = mapped_column(Text, default="")


class SmsRecord(Base):
    __tablename__ = "sms_messages"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    waitlist_entry_id: Mapped[str] = mapped_column(ForeignKey("waitlist_entries.id", ondelete="CASCADE"), index=True)
    phone_number: Mapped[str] = mapped_column(String(40))
    message_type: Mapped[str] = mapped_column(String(40))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AccessTokenRecord(Base):
    __tablename__ = "access_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    staff_id: Mapped[str] = mapped_column(ForeignKey("staff_users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[int] = mapped_column(Integer, index=True)

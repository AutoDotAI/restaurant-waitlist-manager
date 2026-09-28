from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..auth import CurrentStaff, hash_password
from ..entities import AccessTokenRecord, RestaurantRecord, StaffRecord
from ..models import NewStaff, Restaurant, RestaurantPatch, StaffUser
from ..store import get_db, new_id, recalculate_queue, restaurant_to_api, staff_to_api

router = APIRouter(tags=["Restaurant"])


def restaurant_record(db: Session) -> RestaurantRecord:
    record = db.scalar(select(RestaurantRecord).order_by(RestaurantRecord.id).limit(1))
    if record is None:
        raise HTTPException(status_code=404, detail="Restaurant not found.")
    return record


@router.get("/restaurant", response_model=Restaurant)
def get_restaurant(
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> Restaurant:
    del user
    return restaurant_to_api(restaurant_record(db))


@router.patch("/restaurant", response_model=Restaurant)
def update_restaurant(
    payload: RestaurantPatch,
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> Restaurant:
    del user
    record = restaurant_record(db)
    field_map = {
        "slug": "slug",
        "name": "name",
        "timezone": "timezone",
        "phoneCountryCode": "phone_country_code",
        "remoteJoinEnabled": "remote_join_enabled",
        "arrivalWindowMinutes": "arrival_window_minutes",
        "gracePeriodMinutes": "grace_period_minutes",
        "maxPartySize": "max_party_size",
        "baseWaitPerGroupMinutes": "base_wait_per_group_minutes",
        "smsSenderName": "sms_sender_name",
    }
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field_map[field], value)
    recalculate_queue(db, record)
    db.commit()
    db.refresh(record)
    return restaurant_to_api(record)


@router.get("/restaurant/staff", response_model=list[StaffUser])
def list_staff(
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> list[StaffUser]:
    del user
    records = db.scalars(select(StaffRecord).order_by(StaffRecord.name)).all()
    return [staff_to_api(record) for record in records]


@router.post("/restaurant/staff", response_model=StaffUser, status_code=status.HTTP_201_CREATED)
def add_staff(
    payload: NewStaff,
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> StaffUser:
    del user
    if db.scalar(select(StaffRecord.id).where(func.lower(StaffRecord.email) == str(payload.email).lower())):
        raise HTTPException(status_code=409, detail="A staff account already uses that email.")
    restaurant = restaurant_record(db)
    record = StaffRecord(
        id=new_id("staff"), restaurant_id=restaurant.id,
        name=payload.name, email=str(payload.email), role=payload.role,
        password_hash=hash_password(payload.password) if payload.password is not None else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return staff_to_api(record)


@router.delete("/restaurant/staff/{staffId}")
def remove_staff(
    staffId: str,
    user: CurrentStaff,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    del user
    record = db.get(StaffRecord, staffId)
    if record is None:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    db.execute(delete(AccessTokenRecord).where(AccessTokenRecord.staff_id == staffId))
    db.delete(record)
    db.commit()
    return {"success": True}

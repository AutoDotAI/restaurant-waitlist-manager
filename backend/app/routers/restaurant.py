from fastapi import APIRouter, HTTPException, Request, status

from ..auth import CurrentStaff, hash_password
from ..models import NewStaff, Restaurant, RestaurantPatch, StaffUser

router = APIRouter(tags=["Restaurant"])


@router.get("/restaurant", response_model=Restaurant)
def get_restaurant(request: Request, user: CurrentStaff) -> Restaurant:
    del user
    return request.app.state.store.restaurant


@router.patch("/restaurant", response_model=Restaurant)
def update_restaurant(payload: RestaurantPatch, request: Request, user: CurrentStaff) -> Restaurant:
    del user
    store = request.app.state.store
    changes = payload.model_dump(exclude_unset=True)
    store.restaurant = store.restaurant.model_copy(update=changes)
    store.recalculate()
    return store.restaurant


@router.get("/restaurant/staff", response_model=list[StaffUser])
def list_staff(request: Request, user: CurrentStaff) -> list[StaffUser]:
    del user
    return [account.user for account in request.app.state.store.staff.values()]


@router.post("/restaurant/staff", response_model=StaffUser, status_code=status.HTTP_201_CREATED)
def add_staff(payload: NewStaff, request: Request, user: CurrentStaff) -> StaffUser:
    del user
    store = request.app.state.store
    if store.staff_by_email(str(payload.email)):
        raise HTTPException(status_code=409, detail="A staff account already uses that email.")
    staff_user = StaffUser(
        id=store.new_id("staff"), restaurantId=store.restaurant.id,
        name=payload.name, email=payload.email, role=payload.role,
    )
    password_hash = hash_password(payload.password) if payload.password is not None else None
    store.add_staff(staff_user, password_hash)
    return staff_user


@router.delete("/restaurant/staff/{staffId}")
def remove_staff(staffId: str, request: Request, user: CurrentStaff) -> dict[str, bool]:
    del user
    store = request.app.state.store
    if store.staff_by_id(staffId) is None:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    store.remove_staff(staffId)
    return {"success": True}

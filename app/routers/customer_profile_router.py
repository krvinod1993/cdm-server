from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.dependencies import get_current_customer
from app.models.customer import Customer

router = APIRouter()


class CustomerProfileOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None
    avatar_url: str | None = None
    city_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerProfileUpdateIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    city_id: int | None = None


class CustomerChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


@router.get("/profile", response_model=CustomerProfileOut)
def get_customer_profile(
    current_customer: Customer = Depends(get_current_customer),
):
    return current_customer


@router.put("/profile", response_model=CustomerProfileOut)
def update_customer_profile(
    payload: CustomerProfileUpdateIn,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    if payload.name is not None:
        current_customer.name = payload.name
    if payload.phone is not None:
        current_customer.phone = payload.phone
    if payload.avatar_url is not None:
        current_customer.avatar_url = payload.avatar_url
    if payload.city_id is not None:
        current_customer.city_id = payload.city_id

    db.commit()
    db.refresh(current_customer)
    return current_customer


@router.put("/profile/change-password")
def change_customer_password(
    payload: CustomerChangePasswordIn,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    if not current_customer.password_hash or not verify_password(
        payload.current_password,
        current_customer.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_customer.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

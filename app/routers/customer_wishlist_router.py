from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_customer
from app.models.car import Vehicle
from app.models.customer import Customer
from app.models.wishlist import Wishlist
from app.schemas.car import VehiclePublic

router = APIRouter()


@router.post("/{vehicle_id}")
def add_to_wishlist(
    vehicle_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    existing = (
        db.query(Wishlist)
        .filter(
            Wishlist.user_id == current_customer.id,
            Wishlist.vehicle_id == vehicle_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle already in wishlist",
        )

    wishlist_item = Wishlist(
        user_id=current_customer.id,
        vehicle_id=vehicle_id,
    )
    db.add(wishlist_item)
    db.commit()

    return {"message": "Added to wishlist"}


@router.delete("/{vehicle_id}")
def remove_from_wishlist(
    vehicle_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    wishlist_item = (
        db.query(Wishlist)
        .filter(
            Wishlist.user_id == current_customer.id,
            Wishlist.vehicle_id == vehicle_id,
        )
        .first()
    )
    if not wishlist_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found",
        )

    db.delete(wishlist_item)
    db.commit()
    return {"message": "Removed from wishlist"}


@router.get("/", response_model=list[VehiclePublic])
def list_wishlist(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return (
        db.query(Vehicle)
        .join(Wishlist, Wishlist.vehicle_id == Vehicle.id)
        .filter(Wishlist.user_id == current_customer.id)
        .order_by(Wishlist.created_at.desc())
        .all()
    )

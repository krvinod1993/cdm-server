from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.car import Vehicle
from app.models.city import City
from app.models.dealer import Dealer
from app.schemas.car import PaginatedPublicVehiclesResponse, PublicVehicleDetail

router = APIRouter(prefix="/api/public", tags=["Public Vehicles"])


@router.get("/vehicles", response_model=PaginatedPublicVehiclesResponse)
def list_public_vehicles(
    search: str | None = Query(None, description="Search by name or brand (case-insensitive)"),
    brand: str | None = Query(None, description="Filter by exact brand name"),
    city_slug: str | None = Query(None, description="Filter by city slug (e.g. noida)"),
    min_price: int | None = Query(None, ge=0, description="Minimum price"),
    max_price: int | None = Query(None, ge=0, description="Maximum price"),
    sort: str | None = Query(None, pattern="^(price_asc|price_desc)$", description="Sort by price"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    query = db.query(Vehicle).join(Dealer)
    query = query.filter(Vehicle.status.ilike("active"))
    query = query.filter(Dealer.subscription_status.in_(["ACTIVE", "TRIAL"]))

    if city_slug:
        query = query.join(City, Dealer.city_id == City.id)
        query = query.filter(City.slug == city_slug)

    if search:
        query = query.filter(
            or_(
                Vehicle.name.ilike(f"%{search}%"),
                Vehicle.brand.ilike(f"%{search}%"),
            )
        )

    if brand:
        query = query.filter(Vehicle.brand == brand)

    if min_price is not None:
        query = query.filter(Vehicle.price >= min_price)

    if max_price is not None:
        query = query.filter(Vehicle.price <= max_price)

    if sort == "price_asc":
        query = query.order_by(Vehicle.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Vehicle.price.desc())
    else:
        query = query.order_by(Vehicle.created_at.desc())

    total = query.count()
    offset = (page - 1) * limit
    vehicles = query.offset(offset).limit(limit).all()

    return {
        "data": vehicles,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/vehicles/{vehicle_id}", response_model=PublicVehicleDetail)
def get_public_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """
    Get a single active vehicle by ID — no authentication required.

    Returns full vehicle info including specifications and dealer name.
    Only returns the vehicle if its status is 'active'.
    """
    vehicle = (
        db.query(Vehicle)
        .join(Dealer, Vehicle.dealer_id == Dealer.id)
        .filter(
            Vehicle.id == vehicle_id,
            Vehicle.status == "active",
            Dealer.subscription_status.in_(("ACTIVE", "TRIAL")),
        )
        .first()
    )

    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    return vehicle

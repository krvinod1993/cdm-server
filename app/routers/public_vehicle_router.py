from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.car import Vehicle
from app.models.dealer import Dealer
from app.schemas.car import PaginatedPublicVehiclesResponse, PublicVehicleDetail

router = APIRouter(prefix="/api/public", tags=["Public Vehicles"])

# Whitelist of sortable columns → SQLAlchemy column mapping
_SORT_FIELD_MAP = {
    "price": Vehicle.price,
    "year": Vehicle.created_at,   # placeholder until a year column is added
    "created_at": Vehicle.created_at,
}


@router.get("/vehicles", response_model=PaginatedPublicVehiclesResponse)
def list_public_vehicles(
    search: str | None = Query(None, description="Search by vehicle name (case-insensitive)"),
    brand: str | None = Query(None, description="Filter by exact brand name"),
    dealer_id: int | None = Query(None, description="Filter by dealer ID"),
    category_id: int | None = Query(None, description="Filter by category"),
    min_price: float | None = Query(None, ge=0, description="Minimum price"),
    max_price: float | None = Query(None, ge=0, description="Maximum price"),
    sort_by: str | None = Query(
        None,
        pattern="^(price|year|created_at)$",
        description="Sort field: price, year, or created_at",
    ),
    sort_order: str = Query(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort direction: asc or desc",
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Browse all active vehicles — no authentication required.

    Returns only vehicles with status = 'active'.
    Includes category name and dealer name.
    Supports filtering, sorting, and pagination.
    """
    query = (
        db.query(Vehicle)
        .join(Dealer, Vehicle.dealer_id == Dealer.id)
        .filter(
            Vehicle.status == "active",
            Dealer.subscription_status.in_(("ACTIVE", "TRIAL")),
        )
    )

    # ── Filters ──────────────────────────────────────
    if search:
        query = query.filter(Vehicle.name.ilike(f"%{search}%"))

    if brand:
        query = query.filter(Vehicle.brand.ilike(f"%{brand}%"))

    if dealer_id:
        query = query.filter(Vehicle.dealer_id == dealer_id)

    if category_id is not None:
        query = query.filter(Vehicle.category_id == category_id)

    if min_price is not None:
        query = query.filter(Vehicle.price >= min_price)

    if max_price is not None:
        query = query.filter(Vehicle.price <= max_price)

    # ── Total count (after filters, before pagination) ──
    total = query.count()

    # ── Sorting ──────────────────────────────────────
    sort_column = _SORT_FIELD_MAP.get(sort_by, Vehicle.created_at)
    order = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    query = query.order_by(order)

    # ── Pagination ───────────────────────────────────
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

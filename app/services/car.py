from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.car import Vehicle
from app.models.city import City
from app.models.dealer import Dealer


def get_marketplace_vehicles(
    db: Session,
    *,
    city_slug: str | None = None,
    search: str | None = None,
    brand: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str | None = None,
    page: int = 1,
    limit: int = 12,
) -> dict:
    """
    Return paginated marketplace vehicle listings from active cities.

    Parameters
    ----------
    city_slug : str, optional
        Filter vehicles whose dealer belongs to this city.
    search, brand, min_price, max_price : optional filters.
    sort : 'price_asc' or 'price_desc'.
    page, limit : pagination controls.

    Returns
    -------
    dict
        {items: list[Vehicle], total: int, page: int, limit: int}
    """
    query = (
        db.query(Vehicle)
        .join(Dealer)
        .join(City)
        .filter(City.is_active == True)
    )

    # ── City filter ──────────────────────────────────
    if city_slug:
        query = query.filter(City.slug == city_slug)

    # ── Search & filters ─────────────────────────────
    if search:
        query = query.filter(Vehicle.name.ilike(f"%{search}%"))

    if brand:
        query = query.filter(Vehicle.brand == brand)

    if min_price is not None:
        query = query.filter(Vehicle.price >= min_price)

    if max_price is not None:
        query = query.filter(Vehicle.price <= max_price)

    # ── Total count (after filters, before pagination)
    total = query.count()

    # ── Sorting ──────────────────────────────────────
    if sort == "price_asc":
        query = query.order_by(Vehicle.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Vehicle.price.desc())
    else:
        query = query.order_by(Vehicle.created_at.desc())

    # ── Pagination ───────────────────────────────────
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


def get_vehicle_by_id(db: Session, vehicle_id: int) -> Vehicle:
    """
    Return a single vehicle by ID.

    Raises
    ------
    HTTPException 404
        If the vehicle does not exist.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )
    return vehicle

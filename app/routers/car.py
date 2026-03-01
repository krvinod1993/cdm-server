import json
import os
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import UPLOAD_DIR
from app.core.trial import require_active_subscription
from app.db.session import get_db
from app.models.car import Vehicle
from app.models.dealer import Dealer
from app.models.lead import Lead
from app.models.user import User
from app.schemas.car import VehicleBase, VehicleDetail, VehiclePublic, PaginatedVehicleResponse, PaginatedVehiclesResponse
from app.core.security import get_current_dealer, get_current_user
from app.services.car import get_vehicle_by_id
from app.utils.permissions import require_permission

router = APIRouter(prefix="/api", tags=["Vehicles"])


# ── Dealer's own vehicles (authenticated) ────────────

@router.get("/vehicles", response_model=PaginatedVehiclesResponse)
def list_vehicles(
    search: str | None = Query(None, description="Search by vehicle name (case-insensitive)"),
    brand: str | None = Query(None, description="Filter by exact brand name"),
    min_price: float | None = Query(None, ge=0, description="Minimum price"),
    max_price: float | None = Query(None, ge=0, description="Maximum price"),
    sort: str | None = Query(None, pattern="^(price_asc|price_desc)$", description="Sort: price_asc or price_desc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(12, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _sub: None = Depends(require_active_subscription),
):
    """
    List vehicles belonging to the authenticated dealer.

    Query Parameters
    ----------------
    search, brand, min_price, max_price : optional filters.
    sort : 'price_asc' or 'price_desc'.
    page, limit : pagination controls.

    Returns
    -------
    PaginatedVehiclesResponse
        items, total, page, limit
    """
    query = db.query(Vehicle).filter(Vehicle.dealer_id == current_user.dealer_id)

    # ── Filters ─────────────────────────────────────
    if search:
        query = query.filter(Vehicle.name.ilike(f"%{search}%"))

    if brand:
        query = query.filter(Vehicle.brand == brand)

    if min_price is not None:
        query = query.filter(Vehicle.price >= min_price)

    if max_price is not None:
        query = query.filter(Vehicle.price <= max_price)

    # ── Total count (after filters, before pagination) ──
    total = query.count()

    # ── Sorting ─────────────────────────────────────
    if sort == "price_asc":
        query = query.order_by(Vehicle.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Vehicle.price.desc())
    else:
        query = query.order_by(Vehicle.created_at.desc())

    # ── Pagination ──────────────────────────────────
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/vehicles/{vehicle_id}", response_model=VehicleDetail)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """
    Get a single vehicle by ID — includes full dealer info.

    Path Parameters
    ---------------
    vehicle_id : int

    Returns
    -------
    VehicleDetail
        Full vehicle info + nested dealer with city.

    Raises
    ------
    404
        Vehicle not found.
    """
    return get_vehicle_by_id(db, vehicle_id)


# ── Dashboard stats ───────────────────────────────────

class DashboardStatsOut(BaseModel):
    total_vehicles: int
    total_leads: int
    leads_today: int


class VehicleStatusUpdateIn(BaseModel):
    status: Literal["active", "inactive", "sold", "draft"]


@router.get("/dashboard-stats", response_model=DashboardStatsOut)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unified dashboard stats for the current dealer.

    **Not gated by subscription status** — expired dealers can still
    view their aggregate counts.

    - **total_vehicles**: all vehicles belonging to the dealer, regardless of status
    - **total_leads**: all-time lead count for the dealer
    - **leads_today**: leads created today
    """
    dealer_id = current_user.dealer_id

    total_vehicles = (
        db.query(func.count(Vehicle.id))
        .filter(Vehicle.dealer_id == dealer_id)
        .scalar()
    )

    total_leads = (
        db.query(func.count(Lead.id))
        .filter(Lead.dealer_id == dealer_id)
        .scalar()
    )

    leads_today = (
        db.query(func.count(Lead.id))
        .filter(
            Lead.dealer_id == dealer_id,
            func.date(Lead.created_at) == date.today(),
        )
        .scalar()
    )

    return DashboardStatsOut(
        total_vehicles=total_vehicles,
        total_leads=total_leads,
        leads_today=leads_today,
    )


@router.patch("/dealer/vehicles/{vehicle_id}/status", response_model=VehicleBase)
def update_dealer_vehicle_status(
    vehicle_id: int,
    payload: VehicleStatusUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.dealer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dealer account required",
        )

    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if vehicle.dealer_id != current_user.dealer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this vehicle",
        )

    vehicle.status = payload.status
    db.commit()
    db.refresh(vehicle)
    return vehicle


# ── Legacy / Dashboard ───────────────────────────────

@router.get("/home", response_model=list[VehicleBase])
def home_vehicles(db: Session = Depends(get_db)):
    return (
        db.query(Vehicle)
        .join(Dealer, Vehicle.dealer_id == Dealer.id)
        .filter(
            Vehicle.status == "active",
            Dealer.subscription_status != "EXPIRED",
        )
        .all()
    )


@router.get("/inventory", response_model=PaginatedVehicleResponse)
def public_inventory(
    search: str | None = Query(None, description="Filter by name (contains, case-insensitive)"),
    brand: str | None = Query(None, description="Filter by exact brand name"),
    min_price: float | None = Query(None, ge=0, description="Minimum price"),
    max_price: float | None = Query(None, ge=0, description="Maximum price"),
    sort: str | None = Query(None, pattern="^(price_asc|price_desc)$", description="Sort order: price_asc or price_desc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(6, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Vehicle)
        .join(Dealer, Vehicle.dealer_id == Dealer.id)
        .filter(
            Vehicle.status == "active",
            Dealer.subscription_status != "EXPIRED",
        )
    )

    # ── Filters ─────────────────────────────────────
    if search:
        query = query.filter(Vehicle.name.ilike(f"%{search}%"))

    if brand:
        query = query.filter(Vehicle.brand == brand)

    if min_price is not None:
        query = query.filter(Vehicle.price >= min_price)

    if max_price is not None:
        query = query.filter(Vehicle.price <= max_price)

    # ── Total count (after filters, before pagination) ──
    total = query.count()

    # ── Sorting ─────────────────────────────────────
    if sort == "price_asc":
        query = query.order_by(Vehicle.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Vehicle.price.desc())

    # ── Pagination ──────────────────────────────────
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/my-vehicles", response_model=list[VehicleBase])
def my_vehicles(
    dealer_id: int = Depends(get_current_dealer),
    db: Session = Depends(get_db),
):
    return db.query(Vehicle).filter(Vehicle.dealer_id == dealer_id).all()


@router.post("/vehicles", response_model=VehicleBase, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    name: str = Form(...),
    brand: str = Form(...),
    price: float = Form(...),
    category_id: int | None = Form(None),
    specifications: str | None = Form(None, description="JSON string of vehicle specifications"),
    status: str = Form("active"),
    image: UploadFile | None = File(None),
    current_user: User = Depends(require_permission("ADD_VEHICLE")),
    db: Session = Depends(get_db),
    _sub: None = Depends(require_active_subscription),
):
    # Parse specifications JSON string
    specs_dict = None
    if specifications:
        try:
            specs_dict = json.loads(specifications)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=422,
                detail="specifications must be a valid JSON string",
            )

    image_url = None

    if image and image.filename:
        # Generate unique filename to avoid overwrites
        ext = os.path.splitext(image.filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / unique_name

        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        image_url = f"/uploads/{unique_name}"

    vehicle = Vehicle(
        name=name,
        brand=brand,
        price=price,
        status=status,
        image_url=image_url,
        dealer_id=current_user.dealer_id,
        category_id=category_id,
        specifications=specs_dict,
    )

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    return vehicle


@router.delete("/vehicles/{vehicle_id}")
def delete_vehicle(
    vehicle_id: int,
    dealer_id: int = Depends(get_current_dealer),
    db: Session = Depends(get_db),
    _sub: None = Depends(require_active_subscription),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if vehicle.dealer_id != dealer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this vehicle",
        )

    # Remove image file if it exists
    if vehicle.image_url:
        file_path = UPLOAD_DIR / vehicle.image_url.lstrip("/").replace("uploads/", "", 1)
        if file_path.is_file():
            file_path.unlink()

    db.delete(vehicle)
    db.commit()
    return {"detail": "Vehicle deleted"}


@router.put("/vehicles/{vehicle_id}", response_model=VehicleBase)
async def update_vehicle(
    vehicle_id: int,
    name: str | None = Form(None),
    brand: str | None = Form(None),
    price: float | None = Form(None),
    category_id: int | None = Form(None),
    specifications: str | None = Form(None, description="JSON string of vehicle specifications"),
    vehicle_status: str | None = Form(None, alias="status"),
    image: UploadFile | None = File(None),
    current_user: User = Depends(require_permission("EDIT_VEHICLE")),
    db: Session = Depends(get_db),
    _sub: None = Depends(require_active_subscription),
):
    # Check vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # Verify ownership
    if vehicle.dealer_id != current_user.dealer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this vehicle",
        )

    # Only update fields that were explicitly provided (not None)
    if name is not None:
        vehicle.name = name
    if brand is not None:
        vehicle.brand = brand
    if price is not None:
        vehicle.price = price
    if vehicle_status is not None:
        vehicle.status = vehicle_status
    if category_id is not None:
        vehicle.category_id = category_id

    # Parse and update specifications only if provided
    if specifications is not None:
        try:
            vehicle.specifications = json.loads(specifications)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=422,
                detail="specifications must be a valid JSON string",
            )

    # Handle optional image upload
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / unique_name

        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        vehicle.image_url = f"/uploads/{unique_name}"

    db.commit()
    db.refresh(vehicle)

    return vehicle

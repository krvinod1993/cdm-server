import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import UPLOAD_DIR
from app.db.session import get_db
from app.models.car import Car
from app.schemas.car import CarBase, CarDetail, CarPublic, PaginatedCarResponse, PaginatedCarsResponse
from app.core.security import get_current_dealer
from app.services.car import get_marketplace_cars, get_car_by_id

router = APIRouter(prefix="/api", tags=["Cars"])


# ── Marketplace (public) ─────────────────────────────

@router.get("/cars", response_model=PaginatedCarsResponse)
def list_cars(
    city_slug: str | None = Query(None, description="Filter cars by city slug (e.g. 'noida')"),
    search: str | None = Query(None, description="Search by car name (case-insensitive)"),
    brand: str | None = Query(None, description="Filter by exact brand name"),
    min_price: float | None = Query(None, ge=0, description="Minimum price"),
    max_price: float | None = Query(None, ge=0, description="Maximum price"),
    sort: str | None = Query(None, pattern="^(price_asc|price_desc)$", description="Sort: price_asc or price_desc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(12, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Browse marketplace car listings — optionally filtered by city.

    Query Parameters
    ----------------
    city_slug : str, optional
        Filter cars whose dealer belongs to this city.
    search, brand, min_price, max_price : optional filters.
    sort : 'price_asc' or 'price_desc'.
    page, limit : pagination controls.

    Returns
    -------
    PaginatedCarsResponse
        items: list[CarMarketplace]  (car + dealer summary)
        total, page, limit
    """
    return get_marketplace_cars(
        db,
        city_slug=city_slug,
        search=search,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        page=page,
        limit=limit,
    )


@router.get("/cars/{car_id}", response_model=CarDetail)
def get_car(car_id: int, db: Session = Depends(get_db)):
    """
    Get a single car by ID — includes full dealer info.

    Path Parameters
    ---------------
    car_id : int

    Returns
    -------
    CarDetail
        Full car info + nested dealer with city.

    Raises
    ------
    404
        Car not found.
    """
    return get_car_by_id(db, car_id)


# ── Legacy / Dashboard ───────────────────────────────

@router.get("/home", response_model=list[CarBase])
def home_cars(db: Session = Depends(get_db)):
    return db.query(Car).all()


@router.get("/inventory", response_model=PaginatedCarResponse)
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
    query = db.query(Car)

    # ── Filters ─────────────────────────────────────
    if search:
        query = query.filter(Car.name.ilike(f"%{search}%"))

    if brand:
        query = query.filter(Car.brand == brand)

    if min_price is not None:
        query = query.filter(Car.price >= min_price)

    if max_price is not None:
        query = query.filter(Car.price <= max_price)

    # ── Total count (after filters, before pagination) ──
    total = query.count()

    # ── Sorting ─────────────────────────────────────
    if sort == "price_asc":
        query = query.order_by(Car.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Car.price.desc())

    # ── Pagination ──────────────────────────────────
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/my-cars", response_model=list[CarBase])
def my_cars(
    dealer_id: int = Depends(get_current_dealer),
    db: Session = Depends(get_db),
):
    return db.query(Car).filter(Car.dealer_id == dealer_id).all()


@router.post("/cars", response_model=CarBase, status_code=status.HTTP_201_CREATED)
async def create_car(
    name: str = Form(...),
    brand: str = Form(...),
    price: float = Form(...),
    status: str = Form("active"),
    image: UploadFile | None = File(None),
    dealer_id: int = Depends(get_current_dealer),
    db: Session = Depends(get_db),
):
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

    car = Car(
        name=name,
        brand=brand,
        price=price,
        status=status,
        image_url=image_url,
        dealer_id=dealer_id,
    )

    db.add(car)
    db.commit()
    db.refresh(car)

    return car


@router.delete("/cars/{car_id}")
def delete_car(
    car_id: int,
    dealer_id: int = Depends(get_current_dealer),
    db: Session = Depends(get_db),
):
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    if car.dealer_id != dealer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this car",
        )

    # Remove image file if it exists
    if car.image_url:
        file_path = UPLOAD_DIR / car.image_url.lstrip("/").replace("uploads/", "", 1)
        if file_path.is_file():
            file_path.unlink()

    db.delete(car)
    db.commit()
    return {"detail": "Car deleted"}


@router.put("/cars/{car_id}", response_model=CarBase)
async def update_car(
    car_id: int,
    name: str = Form(...),
    brand: str = Form(...),
    price: float = Form(...),
    car_status: str = Form("active", alias="status"),
    image: UploadFile | None = File(None),
    dealer_id: int = Depends(get_current_dealer),
    db: Session = Depends(get_db),
):
    # Check car exists
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    # Verify ownership
    if car.dealer_id != dealer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this car",
        )

    # Update fields
    car.name = name
    car.brand = brand
    car.price = price
    car.status = car_status

    # Handle optional image upload
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / unique_name

        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        car.image_url = f"/uploads/{unique_name}"

    db.commit()
    db.refresh(car)

    return car

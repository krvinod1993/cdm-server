import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from models import Car
from schemas import CarBase, CarDetail, CarPublic, PaginatedCarResponse
from auth import get_current_dealer

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/api", tags=["Cars"])


@router.get("/home", response_model=list[CarBase])
def list_cars(db: Session = Depends(get_db)):
    return db.query(Car).all()


@router.get("/cars/{car_id}", response_model=CarDetail)
def get_car(car_id: int, db: Session = Depends(get_db)):
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    return car


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
        file_path = os.path.join(UPLOAD_DIR, unique_name)

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
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            car.image_url.lstrip("/"),
        )
        if os.path.isfile(file_path):
            os.remove(file_path)

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
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        car.image_url = f"/uploads/{unique_name}"

    db.commit()
    db.refresh(car)

    return car

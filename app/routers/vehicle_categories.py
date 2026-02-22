from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.vehicle_category import VehicleCategory
from app.schemas.car import VehicleCategoryBase

router = APIRouter(prefix="/api", tags=["Vehicle Categories"])


@router.get("/vehicle-categories", response_model=list[VehicleCategoryBase])
def list_vehicle_categories(db: Session = Depends(get_db)):
    """
    List all active vehicle categories.

    Returns
    -------
    list[VehicleCategoryBase]
        Each category includes: id, name, is_active.
    """
    return (
        db.query(VehicleCategory)
        .filter(VehicleCategory.is_active == True)
        .order_by(VehicleCategory.name)
        .all()
    )

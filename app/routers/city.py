from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.city import CityBase
from app.services.city import get_active_cities

router = APIRouter(prefix="/api", tags=["Cities"])


@router.get("/cities", response_model=list[CityBase])
def list_cities(db: Session = Depends(get_db)):
    """
    List all active cities in the marketplace.

    Returns
    -------
    list[CityBase]
        Each city includes: id, name, slug, is_active.
    """
    return get_active_cities(db)

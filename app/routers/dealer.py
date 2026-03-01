from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dealer import DealerBase, DealerWithVehicles
from app.services.dealer import get_dealers, get_dealer_by_id

router = APIRouter(prefix="/api", tags=["Dealers"])


@router.get("/dealers", response_model=list[DealerBase])
def list_dealers(
    city_slug: str | None = Query(None, description="Filter dealers by city slug (e.g. 'noida')"),
    db: Session = Depends(get_db),
):
    """
    List dealers — optionally filtered by city.

    Query Parameters
    ----------------
    city_slug : str, optional
        When provided, returns only dealers belonging to that city.
        When omitted, returns dealers across all active cities.

    Returns
    -------
    list[DealerBase]
        Each dealer includes: id, name, city_id, city, created_at.
    """
    return get_dealers(db, city_slug)


@router.get("/dealers/{dealer_id}", response_model=DealerWithVehicles)
def get_dealer(dealer_id: int, db: Session = Depends(get_db)):
    """
    Get a single dealer by ID — includes their vehicle listings.

    Path Parameters
    ---------------
    dealer_id : int

    Returns
    -------
    DealerWithVehicles
        Dealer info + list of their vehicles.

    Raises
    ------
    404
        Dealer not found.
    """
    return get_dealer_by_id(db, dealer_id)


@router.get("/public/dealers/{dealer_id}", response_model=DealerWithVehicles)
def get_public_dealer(dealer_id: int, db: Session = Depends(get_db)):
    """
    Public dealer detail endpoint.

    Returns dealer data only when subscription_status is ACTIVE or TRIAL.
    """
    return get_dealer_by_id(db, dealer_id)

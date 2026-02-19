from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.city import City
from app.models.dealer import Dealer
from app.schemas.dealer import DealerRegister


def get_dealers(db: Session, city_slug: str | None = None) -> list[Dealer]:
    """
    Return dealers belonging to active cities.

    Parameters
    ----------
    city_slug : str, optional
        When provided, returns only dealers whose city matches this slug.
        When omitted, returns dealers across all active cities.

    Always returns a list — empty list if no dealers match.
    """
    query = db.query(Dealer).join(City).filter(City.is_active == True)

    if city_slug:
        query = query.filter(City.slug == city_slug)

    return query.order_by(Dealer.name.asc()).all()


def get_dealer_by_id(db: Session, dealer_id: int) -> Dealer:
    """
    Return a single dealer by ID.

    Raises
    ------
    HTTPException 404
        If the dealer does not exist.
    """
    dealer = db.query(Dealer).filter(Dealer.id == dealer_id).first()
    if not dealer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dealer not found",
        )
    return dealer


def register_dealer(payload: DealerRegister, db: Session) -> Dealer:
    """
    Register a new dealer.

    Steps
    -----
    1. Validate that the referenced city exists and is active.
    2. Ensure the email is not already taken.
    3. Hash the password and persist the dealer.

    Returns the newly created Dealer ORM instance (with city loaded).
    """

    # ── Validate city ────────────────────────────────
    city = db.query(City).filter(City.id == payload.city_id).first()

    if not city:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="City not found",
        )

    if not city.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is not available for this city",
        )

    # ── Duplicate email check ────────────────────────
    existing = db.query(Dealer).filter(Dealer.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A dealer with this email already exists",
        )

    # ── Create dealer ────────────────────────────────
    dealer = Dealer(
        name=payload.name,
        city_id=payload.city_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    db.add(dealer)
    db.commit()
    db.refresh(dealer)

    return dealer

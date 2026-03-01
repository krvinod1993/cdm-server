from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.city import City
from app.models.dealer import Dealer
from app.models.permission import Permission
from app.models.user import User
from app.models.user_permission import UserPermission
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
    dealer = (
        db.query(Dealer)
        .filter(
            Dealer.id == dealer_id,
            Dealer.subscription_status.in_(("ACTIVE", "TRIAL")),
        )
        .first()
    )
    if not dealer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dealer not found",
        )
    return dealer


def register_dealer(payload: DealerRegister, db: Session) -> tuple[Dealer, User]:
    """
    Register a new dealer.

    Steps
    -----
    1. Validate that the referenced city exists and is active.
    2. Ensure the email is not already taken.
    3. Hash the password and persist the dealer.

    Returns a tuple of (Dealer, User) ORM instances.
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

    # ── Duplicate email check (against User table) ──
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # ── Create dealer (no email/password on dealer) ──
    now = datetime.now(timezone.utc)
    dealer = Dealer(
        name=payload.name,
        city_id=payload.city_id,
        plan_type="FREE",
        subscription_status="TRIAL",
        trial_start_date=now,
        trial_end_date=now + timedelta(days=90),
    )

    db.add(dealer)
    db.flush()  # get dealer.id without committing yet

    # ── Create user linked to dealer ─────────────────
    user = User(
        email=payload.email,
        password=hash_password(payload.password),
        global_role="DEALER_OWNER",
        dealer_id=dealer.id,
    )

    db.add(user)
    db.flush()  # get user.id before assigning permissions

    # ── Assign all permissions to owner ───────────────
    all_permissions = db.query(Permission).all()
    for perm in all_permissions:
        db.add(UserPermission(user_id=user.id, permission_id=perm.id))

    db.commit()
    db.refresh(dealer)
    db.refresh(user)

    return dealer, user

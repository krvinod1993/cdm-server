from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user, verify_password, create_access_token
from app.db.session import get_db
from app.models.dealer import Dealer
from app.models.permission import Permission
from app.models.user import User
from app.models.user_permission import UserPermission
from app.schemas.dealer import DealerRegister, DealerLogin, TokenResponse
from app.services.dealer import register_dealer as register_dealer_service

router = APIRouter(prefix="/api", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_dealer(payload: DealerRegister, db: Session = Depends(get_db)):
    dealer, user = register_dealer_service(payload, db)
    token = create_access_token(data={"sub": str(user.id), "dealer_id": dealer.id})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login_dealer(payload: DealerLogin, db: Session = Depends(get_db)):
    # Find user by email
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact your administrator.",
        )

    # Generate JWT with user info
    token = create_access_token(data={
        "sub": str(user.id),
        "global_role": user.global_role,
        "dealer_id": user.dealer_id,
    })

    return TokenResponse(access_token=token)


# ── GET /api/me ──────────────────────────────────────

class MeResponse(BaseModel):
    id: int
    email: str
    global_role: str
    dealer_id: int | None
    is_active: bool
    permissions: list[str]
    plan_type: str | None = None
    subscription_status: str | None = None
    trial_end_date: datetime | None = None

    model_config = {"from_attributes": True}


@router.get("/me", response_model=MeResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perm_codes = [
        code
        for (code,) in (
            db.query(Permission.code)
            .join(UserPermission, UserPermission.permission_id == Permission.id)
            .filter(UserPermission.user_id == current_user.id)
            .all()
        )
    ]

    # Fetch subscription info from the associated dealer
    plan_type = None
    subscription_status = None
    trial_end_date = None

    if current_user.dealer_id is not None:
        dealer = db.query(Dealer).filter(Dealer.id == current_user.dealer_id).first()
        if dealer:
            plan_type = dealer.plan_type
            subscription_status = dealer.subscription_status
            trial_end_date = dealer.trial_end_date

    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        global_role=current_user.global_role,
        dealer_id=current_user.dealer_id,
        is_active=current_user.is_active,
        permissions=perm_codes,
        plan_type=plan_type,
        subscription_status=subscription_status,
        trial_end_date=trial_end_date,
    )

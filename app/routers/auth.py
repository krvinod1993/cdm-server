from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dealer import Dealer
from app.schemas.dealer import DealerBase, DealerRegister, DealerLogin, TokenResponse
from app.core.security import verify_password, create_access_token
from app.services.dealer import register_dealer as register_dealer_service

router = APIRouter(prefix="/api", tags=["Auth"])


@router.post("/register", response_model=DealerBase, status_code=status.HTTP_201_CREATED)
def register_dealer(payload: DealerRegister, db: Session = Depends(get_db)):
    dealer = register_dealer_service(payload, db)
    return dealer


@router.post("/login", response_model=TokenResponse)
def login_dealer(payload: DealerLogin, db: Session = Depends(get_db)):
    # Find dealer by email
    dealer = db.query(Dealer).filter(Dealer.email == payload.email).first()
    if not dealer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(payload.password, dealer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Generate JWT with dealer_id in payload
    token = create_access_token(data={"sub": str(dealer.id)})

    return TokenResponse(access_token=token)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Dealer
from schemas import DealerRegister, DealerLogin, DealerBase, TokenResponse
from auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api", tags=["Auth"])


@router.post("/register", response_model=DealerBase, status_code=status.HTTP_201_CREATED)
def register_dealer(payload: DealerRegister, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = db.query(Dealer).filter(Dealer.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A dealer with this email already exists",
        )

    # Create new dealer with hashed password
    dealer = Dealer(
        name=payload.name,
        city=payload.city,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    db.add(dealer)
    db.commit()
    db.refresh(dealer)

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

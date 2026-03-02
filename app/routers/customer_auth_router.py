from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.customer import Customer
from app.models.customer_refresh_token import CustomerRefreshToken

router = APIRouter()


class CustomerRegisterIn(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    password: str


class CustomerRegisterOut(BaseModel):
    detail: str


class CustomerLoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", response_model=CustomerRegisterOut, status_code=status.HTTP_201_CREATED)
def register_customer(payload: CustomerRegisterIn, db: Session = Depends(get_db)):
    existing_email = db.query(Customer).filter(Customer.email == payload.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    if payload.phone is not None:
        existing_phone = db.query(Customer).filter(Customer.phone == payload.phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered",
            )

    customer = Customer(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        provider="local",
        email_verified=True,
        verification_token=None,
        verification_expires_at=None,
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return CustomerRegisterOut(detail="Customer registered successfully.")


@router.get("/verify")
def verify_customer_email(token: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.verification_token == token).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )

    if (
        customer.verification_expires_at is not None
        and customer.verification_expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token expired",
        )

    customer.email_verified = True
    customer.verification_token = None
    customer.verification_expires_at = None
    db.commit()

    return {"message": "Email verified successfully"}


@router.post("/login")
def login_customer(
    payload: CustomerLoginIn,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.email == payload.email).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials",
        )

    if not customer.password_hash or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials",
        )

    if not customer.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified",
        )

    if not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account disabled",
        )

    access_token = create_access_token(
        data={"customer_id": customer.id},
        expires_delta=timedelta(minutes=15),
    )

    refresh_token = str(uuid4())
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    refresh_token_row = CustomerRefreshToken(
        customer_id=customer.id,
        token=refresh_token,
        expires_at=refresh_expires_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(refresh_token_row)
    db.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )

    return {
        "access_token": access_token,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
        },
    }


@router.post("/refresh")
def refresh_customer_access_token(
    request: Request,
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token_row = (
        db.query(CustomerRefreshToken)
        .filter(
            CustomerRefreshToken.token == refresh_token,
            CustomerRefreshToken.revoked.is_(False),
        )
        .first()
    )
    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if token_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    customer = db.query(Customer).filter(Customer.id == token_row.customer_id).first()
    if not customer or not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account disabled",
        )

    new_access_token = create_access_token(
        data={"customer_id": customer.id},
        expires_delta=timedelta(minutes=15),
    )

    return {"access_token": new_access_token}


@router.post("/logout")
def logout_customer(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        token_row = (
            db.query(CustomerRefreshToken)
            .filter(CustomerRefreshToken.token == refresh_token)
            .first()
        )
        if token_row:
            token_row.revoked = True
            db.commit()

    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

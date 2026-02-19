from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.city import CityBase
from app.schemas.car import CarBase


class DealerBase(BaseModel):
    """Public dealer info — never includes password_hash."""
    id: int
    name: str
    email: str
    city_id: int
    city: CityBase
    created_at: datetime

    model_config = {"from_attributes": True}


class DealerWithCars(DealerBase):
    cars: list[CarBase] = []


# ── Dealer Auth ──────────────────────────────────────

class DealerRegister(BaseModel):
    """Payload for dealer registration."""
    name: str
    city_id: int
    email: EmailStr
    password: str


class DealerLogin(BaseModel):
    """Payload for dealer login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token returned after successful auth."""
    access_token: str
    token_type: str = "bearer"

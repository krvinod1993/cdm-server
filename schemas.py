from datetime import datetime

from pydantic import BaseModel, EmailStr


# ── Car ──────────────────────────────────────────────

class CarBase(BaseModel):
    id: int
    name: str
    brand: str
    price: float
    image_url: str | None = None
    status: str = "active"
    dealer_id: int

    model_config = {"from_attributes": True}


class CarPublic(BaseModel):
    """Public-facing car info — no dealer details exposed."""
    id: int
    name: str
    brand: str
    price: float
    image_url: str | None = None
    status: str = "active"

    model_config = {"from_attributes": True}


class PaginatedCarResponse(BaseModel):
    """Paginated wrapper for public car listings."""
    items: list[CarPublic]
    total: int
    page: int
    limit: int


class CarDetail(CarBase):
    dealer: "DealerBase"


# ── Dealer ───────────────────────────────────────────

class DealerBase(BaseModel):
    """Public dealer info — never includes password_hash."""
    id: int
    name: str
    city: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DealerWithCars(DealerBase):
    cars: list[CarBase] = []


# ── Dealer Auth ──────────────────────────────────────

class DealerRegister(BaseModel):
    """Payload for dealer registration."""
    name: str
    city: str
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


# rebuild forward refs
CarDetail.model_rebuild()

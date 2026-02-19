from pydantic import BaseModel

from app.schemas.city import CityBase


# ── Internal / Dashboard ─────────────────────────────

class CarBase(BaseModel):
    """Full car info for dealer dashboard."""
    id: int
    name: str
    brand: str
    price: float
    image_url: str | None = None
    status: str = "active"
    dealer_id: int

    model_config = {"from_attributes": True}


class CarDetail(CarBase):
    """Single car detail — includes full dealer info."""
    dealer: "DealerBase"  # resolved via model_rebuild() in __init__


# ── Public / Marketplace ─────────────────────────────

class DealerSummary(BaseModel):
    """Lightweight dealer info embedded in marketplace car listings."""
    id: int
    name: str
    city: CityBase

    model_config = {"from_attributes": True}


class CarPublic(BaseModel):
    """Public-facing car info — no dealer details."""
    id: int
    name: str
    brand: str
    price: float
    image_url: str | None = None
    status: str = "active"

    model_config = {"from_attributes": True}


class CarMarketplace(BaseModel):
    """Car listing for marketplace browse — includes dealer summary."""
    id: int
    name: str
    brand: str
    price: float
    image_url: str | None = None
    status: str = "active"
    dealer: DealerSummary

    model_config = {"from_attributes": True}


# ── Paginated Responses ──────────────────────────────

class PaginatedCarResponse(BaseModel):
    """Paginated wrapper for basic car listings (inventory)."""
    items: list[CarPublic]
    total: int
    page: int
    limit: int


class PaginatedCarsResponse(BaseModel):
    """Paginated wrapper for marketplace car listings (with dealer info)."""
    items: list[CarMarketplace]
    total: int
    page: int
    limit: int

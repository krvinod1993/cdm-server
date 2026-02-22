from pydantic import BaseModel

from app.schemas.city import CityBase


# ── Vehicle Category ─────────────────────────────────

class VehicleCategoryBase(BaseModel):
    """Public vehicle-category info."""
    id: int
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Internal / Dashboard ─────────────────────────────

class VehicleBase(BaseModel):
    """Full vehicle info for dealer dashboard."""
    id: int
    name: str
    brand: str
    price: float
    image_url: str | None = None
    status: str = "active"
    dealer_id: int
    category_id: int | None = None
    category_name: str | None = None
    specifications: dict | None = None

    model_config = {"from_attributes": True}


class VehicleDetail(VehicleBase):
    """Single vehicle detail — includes full dealer info."""
    dealer: "DealerBase"  # resolved via model_rebuild() in __init__


# ── Public / Marketplace ─────────────────────────────

class DealerSummary(BaseModel):
    """Lightweight dealer info embedded in marketplace vehicle listings."""
    id: int
    name: str
    city: CityBase

    model_config = {"from_attributes": True}


class VehiclePublic(BaseModel):
    """Public-facing vehicle info — no dealer details."""
    id: int
    name: str
    brand: str
    price: float
    image_url: str | None = None
    status: str = "active"
    category_id: int | None = None
    category_name: str | None = None
    specifications: dict | None = None

    model_config = {"from_attributes": True}


class VehicleMarketplace(BaseModel):
    """Vehicle listing for marketplace browse — includes dealer summary."""
    id: int
    name: str
    brand: str
    price: float
    image_url: str | None = None
    status: str = "active"
    category_id: int | None = None
    category_name: str | None = None
    specifications: dict | None = None
    dealer: DealerSummary

    model_config = {"from_attributes": True}


# ── Public (unauthenticated) ─────────────────────────

class PublicVehicleListItem(BaseModel):
    """Vehicle listing for public browse — includes dealer name and category."""
    id: int
    name: str
    brand: str
    price: float
    image_url: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    dealer_name: str | None = None

    model_config = {"from_attributes": True}


class PublicVehicleDetail(BaseModel):
    """Single vehicle detail for public view — includes specs and dealer name."""
    id: int
    name: str
    brand: str
    price: float
    image_url: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    specifications: dict | None = None
    dealer_name: str | None = None

    model_config = {"from_attributes": True}


# ── Paginated Responses ──────────────────────────────

class PaginatedVehicleResponse(BaseModel):
    """Paginated wrapper for basic vehicle listings (inventory)."""
    items: list[VehiclePublic]
    total: int
    page: int
    limit: int


class PaginatedVehiclesResponse(BaseModel):
    """Paginated wrapper for marketplace vehicle listings (with dealer info)."""
    items: list[VehicleMarketplace]
    total: int
    page: int
    limit: int


class PaginatedPublicVehiclesResponse(BaseModel):
    """Paginated wrapper for public vehicle listings."""
    data: list[PublicVehicleListItem]
    total: int
    page: int
    limit: int

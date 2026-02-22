from app.schemas.city import CityBase
from app.schemas.car import (
    VehicleCategoryBase,
    VehicleBase,
    VehiclePublic,
    VehicleMarketplace,
    VehicleDetail,
    DealerSummary,
    PaginatedVehicleResponse,
    PaginatedVehiclesResponse,
)
from app.schemas.dealer import (
    DealerBase,
    DealerWithVehicles,
    DealerRegister,
    DealerLogin,
    TokenResponse,
)

# Resolve cross-module forward references
VehicleDetail.model_rebuild(_types_namespace={"DealerBase": DealerBase})

__all__ = [
    # City
    "CityBase",
    # Vehicle Category
    "VehicleCategoryBase",
    # Vehicle
    "VehicleBase",
    "VehiclePublic",
    "VehicleMarketplace",
    "VehicleDetail",
    "DealerSummary",
    "PaginatedVehicleResponse",
    "PaginatedVehiclesResponse",
    # Dealer
    "DealerBase",
    "DealerWithVehicles",
    "DealerRegister",
    "DealerLogin",
    "TokenResponse",
]

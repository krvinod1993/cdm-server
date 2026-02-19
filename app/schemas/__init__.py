from app.schemas.city import CityBase
from app.schemas.car import (
    CarBase,
    CarPublic,
    CarMarketplace,
    CarDetail,
    DealerSummary,
    PaginatedCarResponse,
    PaginatedCarsResponse,
)
from app.schemas.dealer import (
    DealerBase,
    DealerWithCars,
    DealerRegister,
    DealerLogin,
    TokenResponse,
)

# Resolve cross-module forward references
CarDetail.model_rebuild(_types_namespace={"DealerBase": DealerBase})

__all__ = [
    # City
    "CityBase",
    # Car
    "CarBase",
    "CarPublic",
    "CarMarketplace",
    "CarDetail",
    "DealerSummary",
    "PaginatedCarResponse",
    "PaginatedCarsResponse",
    # Dealer
    "DealerBase",
    "DealerWithCars",
    "DealerRegister",
    "DealerLogin",
    "TokenResponse",
]

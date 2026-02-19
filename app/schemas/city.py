from pydantic import BaseModel


class CityBase(BaseModel):
    """Public city info."""
    id: int
    name: str
    slug: str
    is_active: bool

    model_config = {"from_attributes": True}

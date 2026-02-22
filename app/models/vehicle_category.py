from sqlalchemy import Boolean, Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class VehicleCategory(Base):
    __tablename__ = "vehicle_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, server_default="true", nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    vehicles = relationship("Vehicle", back_populates="category", lazy="selectin")

    def __repr__(self) -> str:
        return f"<VehicleCategory {self.name}>"

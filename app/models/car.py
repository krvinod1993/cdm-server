from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    image_url = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, server_default="active")
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("vehicle_categories.id"), nullable=True)
    specifications = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    dealer = relationship("Dealer", back_populates="vehicles", lazy="selectin")
    category = relationship("VehicleCategory", back_populates="vehicles", lazy="selectin")
    leads = relationship("Lead", back_populates="vehicle", cascade="all, delete")

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None

    @property
    def dealer_name(self) -> str | None:
        return self.dealer.name if self.dealer else None

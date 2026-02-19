from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=False)
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    car = relationship("Car", back_populates="leads", lazy="selectin")
    dealer = relationship("Dealer", back_populates="leads", lazy="selectin")

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    image_url = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, server_default="active")
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    dealer = relationship("Dealer", back_populates="cars", lazy="selectin")

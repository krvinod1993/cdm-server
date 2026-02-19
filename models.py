from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from database import Base


class Dealer(Base):
    __tablename__ = "dealers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    cars = relationship("Car", back_populates="dealer", lazy="selectin")


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    image_url = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, server_default="active")
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=False)

    dealer = relationship("Dealer", back_populates="cars", lazy="selectin")

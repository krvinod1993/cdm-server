from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Dealer(Base):
    __tablename__ = "dealers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    city = relationship("City", back_populates="dealers", lazy="selectin")
    cars = relationship("Car", back_populates="dealer", lazy="selectin")
    leads = relationship("Lead", back_populates="dealer", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<Dealer {self.name}>"

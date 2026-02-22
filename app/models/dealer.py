from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Dealer(Base):
    __tablename__ = "dealers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    plan_type = Column(String(50), nullable=False, default="FREE")
    subscription_status = Column(String(50), nullable=False, default="TRIAL")
    trial_start_date = Column(DateTime(timezone=True), nullable=True)
    trial_end_date = Column(DateTime(timezone=True), nullable=True)

    city = relationship("City", back_populates="dealers", lazy="selectin")
    vehicles = relationship("Vehicle", back_populates="dealer", lazy="selectin")
    leads = relationship("Lead", back_populates="dealer", cascade="all, delete")
    users = relationship("User", back_populates="dealer", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<Dealer {self.name}>"

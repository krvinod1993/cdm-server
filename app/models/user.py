from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    global_role = Column(String(50), default="USER")
    dealer_id = Column(Integer, ForeignKey("dealers.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dealer = relationship("Dealer", back_populates="users", lazy="selectin")
    permissions = relationship("UserPermission", back_populates="user", cascade="all, delete")
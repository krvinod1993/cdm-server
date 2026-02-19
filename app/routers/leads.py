from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_dealer
from app.db.session import get_db
from app.models.car import Car
from app.models.lead import Lead

router = APIRouter(prefix="/api", tags=["Leads"])


class LeadCreate(BaseModel):
    car_id: int
    name: str
    phone: str
    message: str | None = None


@router.post("/leads")
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    car = db.query(Car).filter(Car.id == payload.car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    lead = Lead(
        car_id=payload.car_id,
        dealer_id=car.dealer_id,
        name=payload.name,
        phone=payload.phone,
        message=payload.message,
    )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return lead


# ── Response schema for my-leads ──────────────────────


class LeadOut(BaseModel):
    id: int
    car_id: int
    car_title: str
    name: str
    phone: str
    message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/my-leads", response_model=list[LeadOut])
def my_leads(
    dealer_id: int = Depends(get_current_dealer),
    db: Session = Depends(get_db),
):
    """
    Return all leads for the currently authenticated dealer,
    ordered by most recent first.
    """
    leads = (
        db.query(Lead)
        .join(Car, Lead.car_id == Car.id)
        .filter(Lead.dealer_id == dealer_id)
        .order_by(Lead.created_at.desc())
        .all()
    )

    return [
        LeadOut(
            id=lead.id,
            car_id=lead.car_id,
            car_title=lead.car.name,
            name=lead.name,
            phone=lead.phone,
            message=lead.message,
            created_at=lead.created_at,
        )
        for lead in leads
    ]

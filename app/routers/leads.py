from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.car import Car
from app.models.lead import Lead

router = APIRouter(prefix="/api/leads", tags=["Leads"])


class LeadCreate(BaseModel):
    car_id: int
    name: str
    phone: str
    message: str | None = None


@router.post("/")
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

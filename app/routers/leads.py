from datetime import date, datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_dealer, get_current_user
from app.core.trial import require_active_subscription
from app.db.session import get_db
from app.models.car import Vehicle
from app.models.lead import Lead
from app.models.user import User
from app.utils.permissions import require_permission

router = APIRouter(prefix="/api", tags=["Leads"])


# ── Enums & Schemas ──────────────────────────────────

class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    CLOSED = "CLOSED"


class LeadCreate(BaseModel):
    vehicle_id: int
    name: str
    phone: str
    message: str | None = None


class LeadStatusUpdate(BaseModel):
    status: LeadStatus


@router.post("/leads")
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == payload.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    lead = Lead(
        vehicle_id=payload.vehicle_id,
        dealer_id=vehicle.dealer_id,
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
    vehicle_id: int
    vehicle_title: str
    name: str
    phone: str
    message: str | None = None
    status: str = "NEW"
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/my-leads", response_model=list[LeadOut])
def my_leads(
    current_user: User = Depends(require_permission("VIEW_LEADS")),
    db: Session = Depends(get_db),
):
    """
    Return all leads for the currently authenticated dealer,
    ordered by most recent first.
    """
    leads = (
        db.query(Lead)
        .join(Vehicle, Lead.vehicle_id == Vehicle.id)
        .filter(Lead.dealer_id == current_user.dealer_id)
        .order_by(Lead.created_at.desc())
        .all()
    )

    return [
        LeadOut(
            id=lead.id,
            vehicle_id=lead.vehicle_id,
            vehicle_title=lead.vehicle.name,
            name=lead.name,
            phone=lead.phone,
            message=lead.message,
            status=lead.status,
            created_at=lead.created_at,
        )
        for lead in leads
    ]


# ── Lead stats ────────────────────────────────────────


class LeadStatsOut(BaseModel):
    total: int
    today: int


@router.get("/lead-stats", response_model=LeadStatsOut)
def lead_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return aggregate lead counts for the current dealer.

    - **total**: all-time lead count
    - **today**: leads created today

    No lead details are exposed.
    """
    total = (
        db.query(func.count(Lead.id))
        .filter(Lead.dealer_id == current_user.dealer_id)
        .scalar()
    )

    today = (
        db.query(func.count(Lead.id))
        .filter(
            Lead.dealer_id == current_user.dealer_id,
            func.date(Lead.created_at) == date.today(),
        )
        .scalar()
    )

    return LeadStatsOut(total=total, today=today)


# ── Update lead status ───────────────────────────────


@router.put("/leads/{lead_id}", response_model=LeadOut)
def update_lead_status(
    lead_id: int,
    payload: LeadStatusUpdate,
    current_user: User = Depends(require_permission("VIEW_LEADS")),
    db: Session = Depends(get_db),
    _sub: None = Depends(require_active_subscription),
):
    """
    Update the status of a lead.

    Only the dealer who owns the lead can update it.
    Allowed status values: NEW, CONTACTED, CLOSED.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    if lead.dealer_id != current_user.dealer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this lead",
        )

    lead.status = payload.status.value
    db.commit()
    db.refresh(lead)

    return LeadOut(
        id=lead.id,
        vehicle_id=lead.vehicle_id,
        vehicle_title=lead.vehicle.name,
        name=lead.name,
        phone=lead.phone,
        message=lead.message,
        status=lead.status,
        created_at=lead.created_at,
    )

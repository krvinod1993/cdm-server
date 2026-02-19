from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Dealer
from schemas import DealerBase, DealerWithCars

router = APIRouter(prefix="/api", tags=["Dealers"])


@router.get("/dealers", response_model=list[DealerBase])
def list_dealers(db: Session = Depends(get_db)):
    return db.query(Dealer).all()


@router.get("/dealers/{dealer_id}", response_model=DealerWithCars)
def get_dealer(dealer_id: int, db: Session = Depends(get_db)):
    dealer = db.query(Dealer).filter(Dealer.id == dealer_id).first()
    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")
    return dealer

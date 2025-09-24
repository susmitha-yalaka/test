from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas import InventoryAdjustmentIn, InventoryOut
from app.services.inventory import adjust_inventory

router = APIRouter()


@router.post("/adjust", response_model=InventoryOut)
def adjust(adj: InventoryAdjustmentIn, db: Session = Depends(get_db)):
    try:
        return adjust_inventory(db, adj)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

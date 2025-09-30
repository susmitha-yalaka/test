from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.schemas import InventoryAdjustmentIn, InventoryOut
from app.services.inventory import adjust_inventory

router = APIRouter()
log = logging.getLogger("routers.inventory")


@router.post("/adjust", response_model=InventoryOut)
def adjust(adj: InventoryAdjustmentIn, db: Session = Depends(get_db)):
    log.debug("POST /inventory/adjust | sku=%s action=%s qty=%s", adj.sku, adj.action, adj.qty)
    try:
        out = adjust_inventory(db, adj)
        log.info("Inventory updated | sku=%s -> qty=%s", out.sku, out.quantity)
        return out
    except ValueError as e:
        log.warning("Inventory adjust failed | sku=%s reason=%s", adj.sku, e)
        raise HTTPException(status_code=400, detail=str(e))

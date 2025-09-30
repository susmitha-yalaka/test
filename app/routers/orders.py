from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_db
from app.schemas import OrderCreate, OrderOut, OrderStatusUpdate
from app.services import orders as orders_service
from app.models import OrderStatus

router = APIRouter()
log = logging.getLogger("routers.orders")


@router.get("", response_model=List[OrderOut])
def list_orders(db: Session = Depends(get_db), status: Optional[OrderStatus] = Query(default=None)):
    log.debug("GET /orders | status=%s", status)
    resp = orders_service.list_orders(db, status)
    print(f"resp{resp}")
    log.info("Returned %d orders (status=%s)", len(resp), status or "ALL")
    return resp


@router.get("", response_model=List[OrderOut])
def list_all_orders(db: Session = Depends(get_db)):
    log.debug("GET /orders (all)")
    resp = orders_service.list_all_orders(db)
    log.info("Returned %d order summaries", len(resp))
    return resp


@router.post("", response_model=OrderOut, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    log.debug("POST /orders (create)")
    try:
        out = orders_service.create_order(db, order)
        log.info("Created order id=%s with %d items", out.id, len(out.items or []))
        return out
    except ValueError as e:
        log.warning("Create order failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_status(order_id: str, upd: OrderStatusUpdate, db: Session = Depends(get_db)):
    log.debug("PATCH /orders/%s/status -> %s", order_id, upd.status)
    try:
        out = orders_service.update_order_status(db, order_id, upd)
        log.info("Order status updated | id=%s -> %s", order_id, out.status)
        return out
    except ValueError as e:
        log.warning("Update status failed | id=%s reason=%s", order_id, e)
        raise HTTPException(status_code=404, detail=str(e))

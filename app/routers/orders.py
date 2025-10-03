from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_db
from app.schemas import DropDownOption, OrderCreate, OrderOut, OrderStatusUpdate
from app.services import orders as orders_service
# from app.models import OrderStatus

router = APIRouter()
log = logging.getLogger("routers.orders")


@router.get("", response_model=List[DropDownOption])
def list_orders(
    db: Session = Depends(get_db),
    status: Optional[List] = Query(default=None)
):
    # Normalize to a list of statuses or None
    if status is None:
        statuses = None
    elif isinstance(status, list):
        statuses = status
    else:
        statuses = [status]
    print(f"statuses{statuses}")

    log.debug("GET /orders | status=%s", statuses or "ALL")

    resp = orders_service.orders_list_for_dropdown(db, statuses)
    print(resp)
    print(f"response{jsonable_encoder(resp)}")
    log.info("Returned %d orders (status=%s)", len(resp), statuses or "ALL")

    return JSONResponse(content=jsonable_encoder(resp))


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


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, db: Session = Depends(get_db)):
    log.debug("GET /orders/%s", order_id)
    try:
        out = orders_service.get_order_out(db=db, order_id=order_id)
        log.info("Returned order id=%s with %d items", order_id, len(out.items or []))
        return out
    except ValueError as e:
        log.warning("Order not found: %s", e)
        raise HTTPException(status_code=404, detail=str(e))

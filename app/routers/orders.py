from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas import OrderCreate, OrderOut, OrderStatusUpdate
from app.services import orders as orders_service
from app.models import OrderStatus

router = APIRouter()


@router.get("", response_model=List[OrderOut])
def list_orders(db: Session = Depends(get_db), status: Optional[OrderStatus] = Query(default=None)):
    return orders_service.list_orders(db, status)


@router.get("", response_model=List[OrderOut])
def list_all_orders(db: Session = Depends(get_db), status: Optional[OrderStatus] = Query(default=None)):
    return orders_service.list_all_orders(db, status)


@router.post("", response_model=OrderOut, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    try:
        return orders_service.create_order(db, order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_status(order_id: str, upd: OrderStatusUpdate, db: Session = Depends(get_db)):
    try:
        return orders_service.update_order_status(db, order_id, upd)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

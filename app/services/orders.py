from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Order, OrderItem, ProductVariant, ProductCategory, OrderStatus
from app.schemas import OrderCreate, OrderOut, OrderOutItem, OrderStatusUpdate


def create_order(db: Session, payload: OrderCreate) -> OrderOut:
    order = Order(
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_email=payload.customer_email,
        customer_address=payload.customer_address,
        fulfillment_date=payload.fulfillment_date,
        note=payload.note,
        status=OrderStatus.Pending,
    )
    db.add(order)
    db.flush()  # get order.id

    for it in payload.items:
        variant = db.query(ProductVariant).get(it.item_variant)
        category = db.query(ProductCategory).get(it.category)
        if not variant or not category:
            raise ValueError("Invalid category or SKU")
        db.add(OrderItem(
            order_id=order.id,
            category_id=category.id,
            sku=variant.sku,
            size=it.size,
            color=it.color,
            quantity=it.quantity,
            unit_price=it.unit_price,
        ))
    db.commit()
    db.refresh(order)
    return get_order_out(db, order.id)


def update_order_status(db: Session, order_id: str, upd: OrderStatusUpdate) -> OrderOut:
    order = db.query(Order).get(order_id)
    if not order:
        raise ValueError("Order not found")
    order.status = upd.status
    if upd.note:
        order.note = upd.note
    db.commit()
    db.refresh(order)
    return get_order_out(db, order_id)


def list_orders(db: Session, status: Optional[OrderStatus] = None) -> List[OrderOut]:
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    orders = q.order_by(Order.created_at.desc()).all()
    return [get_order_out(db, o.id) for o in orders]


def list_all_orders(db: Session) -> List[dict]:
    q = db.query(Order).all()
    orders = q.order_by(Order.created_at.desc()).all()

    result = []
    for o in orders:
        result.append({
            "id": o.id,
            "title": f"Id-{o.id}",
            "metadata": f"{o.status} - {o.created_at}"
        })
    return result


def get_order_out(db: Session, order_id: str) -> OrderOut:
    o = db.query(Order).get(order_id)
    if not o:
        raise ValueError("Order not found")
    items = []
    for it in o.items:
        title = it.variant.title if it.variant else it.sku
        items.append(OrderOutItem(
            sku=it.sku, title=title, quantity=it.quantity,
            unit_price=it.unit_price, size=it.size, color=it.color
        ))
    return OrderOut(
        id=o.id, status=o.status, created_at=o.created_at,
        customer_name=o.customer_name, customer_phone=o.customer_phone,
        customer_email=o.customer_email, customer_address=o.customer_address,
        fulfillment_date=o.fulfillment_date, note=o.note, items=items
    )

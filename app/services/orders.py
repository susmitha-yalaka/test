from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
from app.models import Order, OrderItem, ProductVariant, ProductCategory, OrderStatus
from app.schemas import DropDownOption, OrderCreate, OrderOut, OrderOutItem, OrderStatusUpdate


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
    db.flush()

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
    print(f"orders{orders}")
    return [get_order_out(db, o.id) for o in orders]


def list_all_orders(db: Session) -> List[dict]:
    q = db.query(Order)
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
    print(f"[get_order_out] id={order_id}")
    o = (
        db.query(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.variant)
        )
        .filter(Order.id == order_id)
        .one_or_none()
    )
    if not o:
        print(f"[get_order_out] not found: {order_id}")
        raise ValueError("Order not found")

    print(f"[get_order_out] found id={o.id} items={len(o.items or [])}")

    items = []
    for i, it in enumerate(o.items or []):
        v = getattr(it, "variant", None)  # should exist due to FK, but guard anyway
        title = getattr(v, "title", None) or it.sku
        print(f"[item {i}] sku={it.sku} qty={it.quantity} price={it.unit_price} has_variant={bool(v)}")
        items.append(OrderOutItem(
            sku=it.sku, title=title, quantity=it.quantity,
            unit_price=it.unit_price, size=it.size, color=it.color
        ))

    out = OrderOut(
        id=o.id, status=o.status, created_at=o.created_at,
        customer_name=o.customer_name, customer_phone=o.customer_phone,
        customer_email=o.customer_email, customer_address=o.customer_address,
        fulfillment_date=o.fulfillment_date, note=o.note, items=items
    )
    print(f"[get_order_out] done id={out.id} items={len(out.items)}")
    return out


def orders_list_for_dropdown(
    db: Session,
    statuses: Optional[List] = None
) -> List[DropDownOption]:
    q = db.query(Order)

    if statuses:
        q = q.filter(Order.status.in_(statuses))
        print(q)

    orders = q.order_by(Order.created_at.desc()).all()
    print(orders)

    return [
        DropDownOption(
            id=str(o.id),
            title=f"{o.id} — {o.customer_name or ''} ({getattr(o.status, 'name', o.status) or ''})"
        )
        for o in orders if o.id
    ]

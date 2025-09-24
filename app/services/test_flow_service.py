from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.restaurant import Table
from app.models.menu import MenuItem
from app.models.order import Order, OrderItem


def _to_float(x: Union[Decimal, float, int, None]) -> float:
    if x is None:
        return 0.0
    return float(x)


async def _get_table_id_by_number(session: AsyncSession, table_number: str) -> Optional[str]:
    """
    Return Table.id (UUID) for a given human-friendly table_number.
    """
    stmt = select(Table.id).where(Table.table_number == table_number)
    row = await session.execute(stmt)
    val = row.scalar_one_or_none()
    return str(val) if val is not None else None


async def _get_or_create_pending_order(
    session: AsyncSession,
    *,
    table_id: str,
    customer_id: Optional[str] = None,
) -> Order:
    """
    Use an Order with status 'pending' as the cart for a table.
    If none exists, create one.
    """
    stmt = (
        select(Order)
        .where(Order.table_id == table_id, Order.status == "pending")
        .options(selectinload(Order.order_items).selectinload(OrderItem.menu_item))
        .limit(1)
    )
    res = await session.execute(stmt)
    order = res.scalar_one_or_none()
    if order:
        return order

    order = Order(
        table_id=table_id,
        customer_id=customer_id,   # can be None for dine-in without identified customer
        status="pending",
        total_amount=Decimal("0.00"),
    )
    session.add(order)
    await session.flush()  # to get order.id
    # eager collections will be empty initially
    return order


# Dropdown items: [{id, title, description}]
async def fetch_menu(session: AsyncSession, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns available menu items. Keeps external keys 'title' and 'description' for compatibility.
    description holds formatted price.
    """
    stmt = select(MenuItem).where(MenuItem.is_available.is_(True))
    if search:
        stmt = stmt.where(MenuItem.name.ilike(f"%{search}%"))
    # Optional ordering:
    # stmt = stmt.order_by(MenuItem.name.asc())

    res = await session.execute(stmt)
    rows = res.scalars().all()

    items: List[Dict[str, Any]] = []
    for mi in rows:
        price_f = _to_float(mi.price)
        items.append(
            {
                "id": str(mi.id),
                "title": mi.name,
                "description": f"₹{int(price_f)}",
            }
        )
    return items


# Return cart as {"cart": [{id, title, price(float), quantity(int)}]}
async def fetch_cart(session: AsyncSession, table_number: str) -> Dict[str, Any]:
    table_id = await _get_table_id_by_number(session, table_number)
    if not table_id:
        return {"cart": []}

    # pending order == cart
    stmt = (
        select(Order)
        .where(Order.table_id == table_id, Order.status == "pending")
        .options(selectinload(Order.order_items).selectinload(OrderItem.menu_item))
        .limit(1)
    )
    res = await session.execute(stmt)
    order = res.scalar_one_or_none()
    if not order:
        return {"cart": []}

    cart: List[Dict[str, Any]] = []
    for oi in order.order_items:
        mi = oi.menu_item
        cart.append(
            {
                "id": str(oi.id),
                "title": mi.name if mi else "",
                "price": _to_float(oi.price if oi.price is not None else mi.price if mi else 0),
                "quantity": int(oi.quantity or 0),
            }
        )
    return {"cart": cart}


def _get_field(obj: Any, key: str) -> Any:
    """Allow dict or object-like payloads."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


async def add_item_to_cart(
    session: AsyncSession,
    table_number: str,
    payload: Any,
    *,
    customer_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    payload must contain: menu_item_id, quantity
    """
    table_id = await _get_table_id_by_number(session, table_number)
    if not table_id:
        return {"error": "Invalid table"}

    menu_item_id = _get_field(payload, "menu_item_id")
    quantity = int(_get_field(payload, "quantity") or 1)

    if not menu_item_id:
        return {"error": "Menu item id missing"}

    # Ensure menu item exists & available
    stmt = select(MenuItem).where(MenuItem.id == menu_item_id, MenuItem.is_available.is_(True))
    res = await session.execute(stmt)
    mi = res.scalar_one_or_none()
    if not mi:
        return {"error": "Menu item not found or unavailable"}

    # Get/create pending order (cart)
    order = await _get_or_create_pending_order(session, table_id=table_id, customer_id=customer_id)

    # If item already in cart, increment qty; else add new OrderItem with current price snapshot
    existing = next((oi for oi in order.order_items if str(oi.menu_item_id) == str(menu_item_id)), None)
    if existing:
        existing.quantity = int(existing.quantity or 0) + quantity
    else:
        oi = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item_id,
            quantity=quantity,
            price=mi.price,  # snapshot current price
        )
        session.add(oi)

    await session.flush()
    await session.commit()
    return {"message": "Item added to cart"}


async def confirm_order(session: AsyncSession, table_number: str) -> Dict[str, Any]:
    """
    - Finds pending Order for the table (cart)
    - Computes total_amount = sum(quantity * price)
    - Sets status -> 'preparing'
    """
    table_id = await _get_table_id_by_number(session, table_number)
    if not table_id:
        return {"error": "Invalid table"}

    stmt = (
        select(Order)
        .where(Order.table_id == table_id, Order.status == "pending")
        .options(selectinload(Order.order_items))
        .limit(1)
    )
    res = await session.execute(stmt)
    order = res.scalar_one_or_none()
    if not order or not order.order_items:
        return {"error": "Cart is empty"}

    try:
        # Recompute total from items
        total = Decimal("0.00")
        for oi in order.order_items:
            qty = int(oi.quantity or 0)
            price_each = oi.price if isinstance(oi.price, Decimal) else Decimal(str(oi.price or 0))
            total += price_each * qty

        order.total_amount = total
        order.status = "preparing"  # next state after confirmation

        await session.flush()
        await session.commit()
        return {"confirmation_message": "Your order has been placed successfully!"}
    except Exception:
        await session.rollback()
        raise

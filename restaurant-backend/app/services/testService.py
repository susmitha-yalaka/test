from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy import select, insert, delete
from datetime import datetime
from app.core.db import database
from app.models import models


def _to_float(x):
    return float(x) if isinstance(x, Decimal) else x


# Return items for the Dropdown: {id:str, title:str, description:str}
async def fetch_menu(search: Optional[str] = None) -> List[Dict[str, Any]]:
    query = models.menu_items.select()
    if search:
        query = query.where(models.menu_items.c.title.ilike(f"%{search}%"))

    rows = await database.fetch_all(query)
    items: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        price = _to_float(d.get("price", 0))
        items.append({
            "id": str(d["id"]),
            "title": d["title"],
            # description shown to the user; keep it text but computed from float
            "description": f"₹{int(price)}"
        })
    return items


# Return cart as {"cart": list[{id,title,price(float),quantity(int)}]}
async def fetch_cart(table_name: str) -> Dict[str, Any]:
    table_row = await database.fetch_one(
        select(models.tables.c.id).where(models.tables.c.table_name == table_name)
    )
    if not table_row:
        return {"cart": []}

    table_id = table_row.id if hasattr(table_row, "id") else table_row[0]

    query = (
        select(
            models.cart_items.c.id,
            models.menu_items.c.title,
            models.menu_items.c.price,
            models.cart_items.c.quantity,
        )
        .select_from(models.cart_items.join(models.menu_items))
        .where(models.cart_items.c.table_id == table_id)
    )
    rows = await database.fetch_all(query)
    cart: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        cart.append({
            "id": str(d["id"]),
            "title": d["title"],
            "price": _to_float(d["price"]),
            "quantity": int(d["quantity"]),
        })
    return {"cart": cart}


async def add_item_to_cart(table_name: str, payload) -> Dict[str, Any]:
    table_row = await database.fetch_one(
        select(models.tables.c.id).where(models.tables.c.table_name == table_name)
    )
    if not table_row:
        return {"error": "Invalid table"}

    table_id = table_row.id if hasattr(table_row, "id") else table_row[0]

    menu_row = await database.fetch_one(
        select(models.menu_items.c.id).where(models.menu_items.c.id == payload.menu_item_id)
    )
    if not menu_row:
        return {"error": "Menu item not found"}

    await database.execute(
        insert(models.cart_items).values(
            table_id=table_id,
            menu_item_id=payload.menu_item_id,
            quantity=payload.quantity,
        )
    )
    return {"message": "Item added to cart"}


async def confirm_order(table_name: str) -> Dict[str, Any]:
    table_row = await database.fetch_one(
        select(models.tables.c.id).where(models.tables.c.table_name == table_name)
    )
    if not table_row:
        return {"error": "Invalid table"}
    table_id = table_row.id if hasattr(table_row, "id") else table_row[0]

    cart_query = (
        select(
            models.cart_items.c.menu_item_id,
            models.cart_items.c.quantity,
            models.menu_items.c.price,
        )
        .select_from(models.cart_items.join(models.menu_items))
        .where(models.cart_items.c.table_id == table_id)
    )
    cart_items = await database.fetch_all(cart_query)
    if not cart_items:
        return {"error": "Cart is empty"}

    order_id = await database.execute(
        insert(models.orders).values(
            table_id=table_id,
            ordered_at=datetime.utcnow(),
            status="confirmed",
        )
    )

    # Persist order lines (store price at order time as-is; DB column likely Numeric)
    for item in cart_items:
        await database.execute(
            insert(models.order_items).values(
                order_id=order_id,
                menu_item_id=item.menu_item_id,
                quantity=int(item.quantity),
                price_at_order_time=item.price,  # DB handles Decimal/Numeric
            )
        )

    await database.execute(delete(models.cart_items).where(models.cart_items.c.table_id == table_id))
    return {"confirmation_message": "Your order has been placed successfully!"}

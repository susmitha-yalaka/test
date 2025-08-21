# app/services/testService.py

from typing import List, Dict, Any, Optional
from app.core.db import database
from app.schema.testSchema import AddToCartRequest
from app.models import models  # Assumes you have all tables defined in models.py
from sqlalchemy import select, insert, delete
from datetime import datetime


# ✅ Fetch all or filtered menu items
async def fetch_menu(search: Optional[str] = None) -> List[Dict[str, Any]]:
    query = models.menu_items.select()
    if search:
        query = query.where(models.menu_items.c.title.ilike(f"%{search}%"))
    return await database.fetch_all(query)


# ✅ Fetch current cart for a given table
async def fetch_cart(table_name: str) -> Dict[str, Any]:
    # Get the table id from name
    table_row = await database.fetch_one(
        select(models.tables.c.id).where(models.tables.c.table_name == table_name)
    )
    if not table_row:
        return {"cart": []}

    query = (
        select(
            models.cart_items.c.id,
            models.menu_items.c.title,
            models.menu_items.c.price,
            models.cart_items.c.quantity,
        )
        .select_from(models.cart_items.join(models.menu_items))
        .where(models.cart_items.c.table_id == table_row.id)
    )
    cart_items = await database.fetch_all(query)
    return {"cart": [dict(item) for item in cart_items]}


# ✅ Add item to cart
async def add_item_to_cart(table_name: str, payload: AddToCartRequest) -> Dict[str, Any]:
    # Get table ID
    table_row = await database.fetch_one(
        select(models.tables.c.id).where(models.tables.c.table_name == table_name)
    )
    if not table_row:
        return {"error": "Invalid table"}

    # Get menu item ID
    menu_row = await database.fetch_one(
        select(models.menu_items.c.id).where(models.menu_items.c.title == payload.selectedItem)
    )
    if not menu_row:
        return {"error": "Menu item not found"}

    # Insert into cart_items
    query = insert(models.cart_items).values(
        table_id=table_row.id,
        menu_item_id=menu_row.id,
        quantity=payload.quantity,
    )
    await database.execute(query)
    return {"message": "Item added to cart"}


# ✅ Confirm order
async def confirm_order(table_name: str) -> Dict[str, Any]:
    # Get table ID
    table_row = await database.fetch_one(
        select(models.tables.c.id).where(models.tables.c.table_name == table_name)
    )
    if not table_row:
        return {"error": "Invalid table"}

    table_id = table_row.id

    # Get all cart items
    cart_query = (
        select(models.cart_items.c.menu_item_id, models.cart_items.c.quantity, models.menu_items.c.price)
        .select_from(models.cart_items.join(models.menu_items))
        .where(models.cart_items.c.table_id == table_id)
    )
    cart_items = await database.fetch_all(cart_query)

    if not cart_items:
        return {"error": "Cart is empty"}

    # Create order
    order_query = insert(models.orders).values(
        table_id=table_id,
        ordered_at=datetime.utcnow(),
        status="confirmed"
    )
    order_id = await database.execute(order_query)

    # Add items to order_items
    for item in cart_items:
        await database.execute(
            insert(models.order_items).values(
                order_id=order_id,
                menu_item_id=item.menu_item_id,
                quantity=item.quantity,
                price_at_order_time=item.price
            )
        )

    # Clear cart
    delete_query = delete(models.cart_items).where(models.cart_items.c.table_id == table_id)
    await database.execute(delete_query)

    return {"confirmation_message": "Your order has been placed successfully!"}

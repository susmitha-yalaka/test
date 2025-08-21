# app/models/models.py

from sqlalchemy import Table, Column, Integer, String, ForeignKey, DateTime, Numeric, MetaData
from datetime import datetime

metadata = MetaData()

menu_items = Table(
    "menu_items", metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(100), nullable=False),
    Column("description", String),
    Column("price", Numeric(10, 2), nullable=False),
)

tables = Table(
    "tables", metadata,
    Column("id", Integer, primary_key=True),
    Column("table_name", String(50), unique=True, nullable=False),
)

cart_items = Table(
    "cart_items", metadata,
    Column("id", Integer, primary_key=True),
    Column("table_id", Integer, ForeignKey("tables.id")),
    Column("menu_item_id", Integer, ForeignKey("menu_items.id")),
    Column("quantity", Integer, nullable=False),
    Column("added_at", DateTime, default=datetime.utcnow),
)

orders = Table(
    "orders", metadata,
    Column("id", Integer, primary_key=True),
    Column("table_id", Integer, ForeignKey("tables.id")),
    Column("ordered_at", DateTime, default=datetime.utcnow),
    Column("status", String(20), default="confirmed"),
)

order_items = Table(
    "order_items", metadata,
    Column("id", Integer, primary_key=True),
    Column("order_id", Integer, ForeignKey("orders.id")),
    Column("menu_item_id", Integer, ForeignKey("menu_items.id")),
    Column("quantity", Integer, nullable=False),
    Column("price_at_order_time", Numeric(10, 2), nullable=False),
)

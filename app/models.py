import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Date, Enum, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class OrderStatus(str, enum.Enum):
    Pending = "Pending"
    Confirmed = "Confirmed"
    Preparing = "Preparing"
    OutForDelivery = "Out for delivery"
    Delivered = "Delivered"
    Cancelled = "Cancelled"


class ProductCategory(Base):
    __tablename__ = "product_categories"
    id = Column(String, primary_key=True)          # e.g., "skirt"
    title = Column(String, nullable=False)

    variants = relationship("ProductVariant", back_populates="category")


class ProductVariant(Base):
    __tablename__ = "product_variants"
    sku = Column(String, primary_key=True)         # e.g., "SKU-SKIRT-001"
    title = Column(String, nullable=False)         # "Skirt — Pleated — Black — S"
    size = Column(String, nullable=True)
    color = Column(String, nullable=True)

    category_id = Column(ForeignKey("product_categories.id"), index=True, nullable=False)
    category = relationship("ProductCategory", back_populates="variants")

    inventory = relationship("Inventory", back_populates="variant", uselist=False)


class Inventory(Base):
    __tablename__ = "inventory"
    sku = Column(ForeignKey("product_variants.sku"), primary_key=True)
    quantity = Column(Integer, nullable=False, default=0)

    variant = relationship("ProductVariant", back_populates="inventory")


class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, default=lambda: f"BTQ-{uuid.uuid4().hex[:8].upper()}")
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)
    customer_address = Column(Text, nullable=True)

    fulfillment_date = Column(Date, nullable=True)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.Pending)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, autoincrement=True)

    order_id = Column(ForeignKey("orders.id"), index=True, nullable=False)
    order = relationship("Order", back_populates="items")

    category_id = Column(ForeignKey("product_categories.id"), nullable=False)
    category = relationship("ProductCategory")

    sku = Column(ForeignKey("product_variants.sku"), nullable=False)
    variant = relationship("ProductVariant")

    size = Column(String, nullable=True)
    color = Column(String, nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Integer, nullable=True)
    __table_args__ = (
        UniqueConstraint("order_id", "sku", name="uq_order_sku"),
    )

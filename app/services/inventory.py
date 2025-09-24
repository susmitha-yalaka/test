from sqlalchemy.orm import Session
from app.models import Inventory, ProductVariant
from app.schemas import InventoryAdjustmentIn, InventoryOut


def adjust_inventory(db: Session, adj: InventoryAdjustmentIn) -> InventoryOut:
    if not adj.sku:
        raise ValueError("sku is required for inventory adjustment")

    variant = db.query(ProductVariant).get(adj.sku)
    if not variant:
        raise ValueError("Unknown sku")

    inv = db.query(Inventory).get(adj.sku)
    if not inv:
        inv = Inventory(sku=adj.sku, quantity=0)
        db.add(inv)

    if adj.action == "add":
        inv.quantity += adj.qty
    elif adj.action == "remove":
        inv.quantity = max(0, inv.quantity - adj.qty)
    elif adj.action == "set":
        inv.quantity = max(0, adj.qty)
    else:
        raise ValueError("Invalid action")

    db.commit()
    db.refresh(inv)
    return InventoryOut(sku=inv.sku, quantity=inv.quantity)

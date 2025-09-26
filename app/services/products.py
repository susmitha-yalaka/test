# app/services/products.py
from sqlalchemy.orm import Session
from app.models import ProductCategory, ProductVariant
from app.schemas import VariantOut


def list_categories(db: Session):
    """Return all product categories (model instances)."""
    return db.query(ProductCategory).all()


def list_all_variants(db: Session):
    """
    Return SKU variants for a category.
    Router expects List[VariantOut], so we map here.
    """
    variants = (
        db.query(ProductVariant)
        .all()
    )
    return [
        VariantOut(id=v.sku, title=v.title, size=v.size, color=v.color)
        for v in variants
    ]


def list_variants_by_category(db: Session, category_id: str):
    """
    Return SKU variants for a category.
    Router expects List[VariantOut], so we map here.
    """
    variants = (
        db.query(ProductVariant)
        .filter(ProductVariant.category_id == category_id)
        .all()
    )
    return [
        VariantOut(id=v.sku, title=v.title, size=v.size, color=v.color)
        for v in variants
    ]


def upsert_category(db: Session, id: str, title: str) -> ProductCategory:
    cat = db.query(ProductCategory).get(id)
    if not cat:
        cat = ProductCategory(id=id, title=title)
        db.add(cat)
    else:
        cat.title = title
    db.commit()
    db.refresh(cat)
    return cat


def upsert_variant(
    db: Session,
    sku: str,
    title: str,
    category_id: str,
    size: str | None = None,
    color: str | None = None,
) -> ProductVariant:
    var = db.query(ProductVariant).get(sku)
    if not var:
        var = ProductVariant(
            sku=sku, title=title, category_id=category_id, size=size, color=color
        )
        db.add(var)
    else:
        var.title = title
        var.category_id = category_id
        var.size = size
        var.color = color
    db.commit()
    db.refresh(var)
    return var

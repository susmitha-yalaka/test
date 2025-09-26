from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.services.products import list_all_variants, list_categories, list_variants_by_category, upsert_category, upsert_variant
from app.schemas import CategoryOut, VariantOut

router = APIRouter()


@router.get("/categories", response_model=List[CategoryOut])
def categories(db: Session = Depends(get_db)):
    cats = list_categories(db)
    return [{"id": c.id, "title": c.title} for c in cats]


@router.get("/variants", response_model=List[VariantOut])
def all_variants(db: Session = Depends(get_db)):
    return list_all_variants(db)


@router.get("/variants_by_category", response_model=List[VariantOut])
def variants(category: str, db: Session = Depends(get_db)):
    return list_variants_by_category(db, category)


# Optional admin endpoints to add data (since no seed)
@router.post("/categories", response_model=CategoryOut, status_code=201)
def add_category(id: str, title: str, db: Session = Depends(get_db)):
    c = upsert_category(db, id, title)
    return {"id": c.id, "title": c.title}


@router.post("/variants", response_model=VariantOut, status_code=201)
def add_variant(sku: str, title: str, category_id: str, size: str = None, color: str = None, db: Session = Depends(get_db)):
    v = upsert_variant(db, sku, title, category_id, size, color)
    return {"id": v.sku, "title": v.title, "size": v.size, "color": v.color}

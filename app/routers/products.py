from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.database import get_db
from app.services.products import (
    list_all_variants, list_categories, list_variants_by_category,
    upsert_category, upsert_variant
)
from app.schemas import CategoryOut, VariantOut

router = APIRouter()
log = logging.getLogger("routers.products")


@router.get("/categories", response_model=List[CategoryOut])
def categories(db: Session = Depends(get_db)):
    log.debug("GET /products/categories")
    cats = list_categories(db)
    resp = [{"id": c.id, "title": c.title} for c in cats]
    log.info("Returned %d categories", len(resp))
    return resp


@router.get("/variants", response_model=List[VariantOut])
def all_variants(db: Session = Depends(get_db)):
    log.debug("GET /products/variants")
    resp = list_all_variants(db)
    log.info("Returned %d variants", len(resp))
    return resp


@router.get("/variants_by_category", response_model=List[VariantOut])
def variants(category: str, db: Session = Depends(get_db)):
    log.debug("GET /products/variants_by_category | category=%s", category)
    resp = list_variants_by_category(db, category)
    log.info("Returned %d variants for category=%s", len(resp), category)
    return resp


@router.post("/categories", response_model=CategoryOut, status_code=201)
def add_category(id: str, title: str, db: Session = Depends(get_db)):
    log.debug("POST /products/categories | id=%s", id)
    c = upsert_category(db, id, title)
    log.info("Upserted category id=%s", c.id)
    return {"id": c.id, "title": c.title}


@router.post("/variants", response_model=VariantOut, status_code=201)
def add_variant(sku: str, title: str, category_id: str, size: str = None, color: str = None, db: Session = Depends(get_db)):
    log.debug("POST /products/variants | sku=%s category_id=%s", sku, category_id)
    v = upsert_variant(db, sku, title, category_id, size, color)
    log.info("Upserted variant sku=%s", v.sku)
    return {"id": v.sku, "title": v.title, "size": v.size, "color": v.color}

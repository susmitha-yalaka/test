from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ProductCategory, ProductVariant
from app.schemas import VariantOut


async def list_categories(db: AsyncSession):
    res = await db.execute(select(ProductCategory))
    return res.scalars().all()


async def list_variants_by_category(db: AsyncSession, category_id: str):
    res = await db.execute(
        select(ProductVariant).where(ProductVariant.category_id == category_id)
    )
    variants = res.scalars().all()
    return [VariantOut(id=v.sku, sku=v.sku, title=v.title, size=v.size, color=v.color) for v in variants]

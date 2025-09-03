from fastapi import APIRouter
from app.services import testService
from app.schema.test_schema import AddToCartRequest

router = APIRouter(prefix="/restaurant", tags=["Restaurant API"])


@router.get("/menu")
async def get_menu(search: str = None):
    return await testService.fetch_menu(search)


@router.get("/cart/{table_id}")
async def get_cart(table_id: str):
    return await testService.fetch_cart(table_id)


@router.post("/cart/{table_id}/add")
async def add_to_cart(table_id: str, payload: AddToCartRequest):
    return await testService.add_item_to_cart(table_id, payload)


@router.post("/order/{table_id}/confirm")
async def confirm_order(table_id: str):
    return await testService.confirm_order(table_id)

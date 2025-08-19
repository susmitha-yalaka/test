import httpx
from typing import List, Dict, Any, Optional
from app.core import config
from app.schema.testSchema import AddToCartRequest

BASE_URL = config.RESTAURANT_BASE_URL
DEFAULT_TIMEOUT = 10.0


async def fetch_menu(search: Optional[str] = None) -> List[Dict[str, Any]]:
    params = {"search": search} if search else {}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/menu", params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()


async def fetch_cart(table_id: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/cart/{table_id}", timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()


async def add_item_to_cart(table_id: str, payload: AddToCartRequest) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/cart/{table_id}/add",
            json=payload.dict(),
            timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()


async def confirm_order(table_id: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/order/{table_id}/confirm", timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

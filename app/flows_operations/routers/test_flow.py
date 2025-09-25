# app/routers/test_flow.py
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException, Response

from app.core.encryptDecrypt import (
    DecryptedRequestData,
    RequestData,
    decryptRequest,
    encryptResponse,
)

from app.core.database import SessionLocal
from app.services import products as products_service
from app.services import orders as orders_service
from app.models import OrderStatus

router = APIRouter()


def _status_from_any(v: Optional[str]) -> Optional[OrderStatus]:
    if not v or v == "ALL":
        return None
    try:
        return OrderStatus(v)
    except Exception:
        return None


def _order_options(orders) -> List[Dict[str, str]]:
    """Map Order ORM objects -> [{id, title}]"""
    opts = []
    for o in orders:
        # title like: "BTQ-1001 — Asha Menon (Preparing)"
        title = f"{o.id} — {o.customer_name} ({o.status})"
        opts.append({"id": o.id, "title": title})
    return opts


def _variant_options(variants) -> List[Dict[str, str]]:
    """Map Variant models/DTOs -> [{id, title}] (id = sku)"""
    opts = []
    for v in variants:
        sku = getattr(v, "sku", getattr(v, "id", None))  # tolerate either model or schema
        title = getattr(v, "title", None)
        if sku and title:
            opts.append({"id": sku, "title": title})
    return opts


async def processingDecryptedData_boutique(dd: DecryptedRequestData) -> Dict[str, Any]:
    """
    Handle WhatsApp Flow data:
      - VIEW_ORDER: initial -> all orders; data_exchange -> filter by status, return {orderOptions:[...]}
      - NEW_ORDER:  data_exchange(selected_category) -> {variantOptions:[...]} ; initial -> empty list
      - CHOOSE_NAV / MANAGE_INVENTORY: static
    """
    if dd.action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    screen: str = dd.screen or ""
    data_in: Dict[str, Any] = dd.data or {}
    action: Optional[str] = dd.action

    # ---- CHOOSE_NAV (static) ----
    if screen == "CHOOSE_NAV":
        return {"version": "3.0", "screen": "CHOOSE_NAV", "data": {}}

    # ---- VIEW_ORDER (dynamic orderOptions) ----
    if screen == "VIEW_ORDER":
        # Accept either "status" or "status_filter" from client
        status_raw = data_in.get("status") or data_in.get("status_filter") or "ALL"
        status_enum = _status_from_any(status_raw)

        with SessionLocal() as db:
            orders = orders_service.list_orders(db, status_enum)  # service returns ORM list
            options = _order_options(orders)

        if action == "data_exchange":
            # Return only data block for dynamic refresh
            return {"version": "3.0", "data": {"orderOptions": options}}

        # Initial render -> include screen + all orders
        return {"version": "3.0", "screen": "VIEW_ORDER", "data": {"orderOptions": options}}

    # ---- NEW_ORDER (category -> variants as array) ----
    if screen == "NEW_ORDER":
        selected_category = (
            data_in.get("selected_category")
            or data_in.get("item_category")
            or ""
        )
        if action == "data_exchange" and selected_category:
            with SessionLocal() as db:
                variants = products_service.list_variants_by_category(db, selected_category)
                options = _variant_options(variants)
            return {"version": "3.0", "data": {"variantOptions": options}}

        # Initial render
        return {"version": "3.0", "screen": "NEW_ORDER", "data": {"variantOptions": []}}

    # ---- MANAGE_INVENTORY (no dynamic fetch in current JSON) ----
    if screen == "MANAGE_INVENTORY":
        return {"version": "3.0", "screen": "MANAGE_INVENTORY", "data": {}}

    # ---- Fallback ----
    return {"version": "3.0", "screen": screen or "CHOOSE_NAV", "data": {}}


@router.post("/boutiqueFlow")
async def boutique_flow_handler(request: RequestData):
    """
    Encrypted endpoint: decrypt -> process -> encrypt.
    """
    try:
        decryptedDataDict, aes_key, iv = decryptRequest(
            request.encrypted_flow_data,
            request.encrypted_aes_key,
            request.initial_vector,
        )
        decrypted_data = DecryptedRequestData(**decryptedDataDict)
        response_dict = await processingDecryptedData_boutique(decrypted_data)
        encrypted_response = encryptResponse(response_dict, aes_key, iv)
        return Response(content=encrypted_response, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

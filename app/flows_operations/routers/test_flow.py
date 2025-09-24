# app/routers/test_flow.py
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Response

from app.core.encryptDecrypt import (
    DecryptedRequestData,
    RequestData,
    decryptRequest,
    encryptResponse,
)

# Keep logic in services (DB access lives there)
from app.core.database import SessionLocal
from app.services import products as products_service
from app.services import orders as orders_service

router = APIRouter()


async def processingDecryptedData_boutique(dd: DecryptedRequestData) -> Dict[str, Any]:
    """
    Handle decrypted WhatsApp Flow Data API requests for the Boutique flow.
    Returns a plain dict; encryption is applied in the route handler.
    """
    # Health check
    if dd.action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    screen: str = dd.screen or ""
    data_in: Dict[str, Any] = dd.data or {}
    action: Optional[str] = dd.action

    # CHOOSE_NAV (NavigationList-only screen): no dynamic data needed
    if screen == "CHOOSE_NAV":
        return {"version": "3.0", "screen": "CHOOSE_NAV", "data": {}}

    if screen == "VIEW_ORDER":
        status_id = data_in.get("status") or data_in.get("status_filter") or "ALL"
        with SessionLocal() as db:
            out = orders_service.list_orders(db, status_id)
        # On initial load (no data_exchange), also include screen to be explicit
        if action == "data_exchange":
            return {"version": "3.0", "data": out}
        return {"version": "3.0", "screen": "VIEW_ORDER", "data": out}

    if screen == "NEW_ORDER":
        selected_category = (
            data_in.get("selected_category")
            or data_in.get("item_category")
            or ""
        )
        if action == "data_exchange" and selected_category:
            with SessionLocal() as db:
                category = products_service.list_variants_by_category(db, selected_category)
            return {"version": "3.0", "data": category}
        # initial load (or no category selected yet)
        return {"version": "3.0", "screen": "NEW_ORDER", "data": {"variantOptions": {"options": []}}}

    if screen == "MANAGE_INVENTORY":
        return {"version": "3.0", "screen": "MANAGE_INVENTORY", "data": {}}

    # Fallback
    return {"version": "3.0", "screen": screen or "CHOOSE_NAV", "data": {}}


# ---------- HTTP endpoints (encrypted) ----------

@router.post("/boutiqueFlow")
async def boutique_flow_handler(request: RequestData):
    """
    API endpoint for handling Boutique flow requests.
    Decrypts request -> runs business logic -> encrypts response.
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

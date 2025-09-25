# app/routers/test_flow.py
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session  # <-- FIX: use SQLAlchemy Session, not requests.Session

from app.core.encryptDecrypt import (
    DecryptedRequestData,
    RequestData,
    decryptRequest,
    encryptResponse,
)
from app.core.database import get_db
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
    """Map OrderOut/ORM -> [{id, title}]"""
    opts: List[Dict[str, str]] = []
    for o in orders:
        oid = getattr(o, "id", None)
        name = getattr(o, "customer_name", "")
        status = getattr(o, "status", "")
        if oid:
            opts.append({"id": oid, "title": f"{oid} — {name} ({status})"})
    return opts


def _variant_options(variants) -> List[Dict[str, str]]:
    """Map VariantOut/ORM -> [{id, title}] (id=sku)"""
    out: List[Dict[str, str]] = []
    for v in variants:
        vid = getattr(v, "sku", None) or getattr(v, "id", None)
        title = getattr(v, "title", None)
        if vid and title:
            out.append({"id": vid, "title": title})
    return out


async def processingDecryptedData_boutique(
    dd: DecryptedRequestData,
    db: Session,  # <-- DB provided by Depends(get_db)
) -> Dict[str, Any]:
    """
    WhatsApp Flow handler:
      - CHOOSE_NAV: static
      - VIEW_ORDER: initial -> all orders; data_exchange(status) -> filtered {orderOptions:[...]}
      - NEW_ORDER:  data_exchange(selected_category) -> {variantOptions:[...]} ; initial -> empty list
      - MANAGE_INVENTORY: static
    """
    print(f"dd{dd}")
    if dd.action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    screen: str = dd.screen or ""
    data_in: Dict[str, Any] = dd.data or {}
    action: Optional[str] = dd.action

    # ---- CHOOSE_NAV ----
    if screen == "CHOOSE_NAV":
        print("inside 1st screen")
        return {"version": "3.0", "screen": "CHOOSE_NAV", "data": {}}

    # ---- VIEW_ORDER ----
    if screen == "VIEW_ORDER":
        print("inside view order")
        status_raw = data_in.get("status") or data_in.get("status_filter") or "ALL"
        status_enum = _status_from_any(status_raw)

        orders = orders_service.list_orders(db, status_enum)
        options = _order_options(orders)

        if action == "data_exchange":
            print("inside data exchange")
            return {"version": "3.0", "data": {"orderOptions": options}}

        return {"version": "3.0", "screen": "VIEW_ORDER", "data": {"orderOptions": options}}

    # ---- NEW_ORDER ----
    if screen == "NEW_ORDER":
        selected_category = (
            data_in.get("selected_category")
            or data_in.get("item_category")
            or ""
        )

        if action == "data_exchange" and selected_category:
            variants = products_service.list_variants_by_category(db, selected_category)
            options = _variant_options(variants)
            return {"version": "3.0", "data": {"variantOptions": options}}

        return {"version": "3.0", "screen": "NEW_ORDER", "data": {"variantOptions": []}}

    # ---- MANAGE_INVENTORY ----
    if screen == "MANAGE_INVENTORY":
        return {"version": "3.0", "screen": "MANAGE_INVENTORY", "data": {}}

    # ---- Fallback ----
    return {"version": "3.0", "screen": screen or "CHOOSE_NAV", "data": {}}


@router.post("/boutiqueFlow")
async def boutique_flow_handler(
    request: RequestData,
    db: Session = Depends(get_db),  # <-- inject here
):
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
        print(f"decrypted_data{decrypted_data}")
        response_dict = await processingDecryptedData_boutique(decrypted_data, db)
        encrypted_response = encryptResponse(response_dict, aes_key, iv)
        return Response(content=encrypted_response, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# app/routers/test_flow.py
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

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

# ---------- helpers ----------


def _status_from_any(v: Optional[str]) -> Optional[OrderStatus]:
    if not v or v == "ALL":
        return None
    try:
        return OrderStatus(v)
    except Exception:
        return None


def _map_categories(cats) -> List[Dict[str, str]]:
    return [{"id": getattr(c, "id", ""), "title": getattr(c, "title", "")} for c in cats]


def _map_variants(variants) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for v in variants:
        vid = getattr(v, "sku", None) or getattr(v, "id", None)
        title = getattr(v, "title", None)
        if vid and title:
            out.append({"id": vid, "title": title})
    return out


def _map_orders(orders) -> List[Dict[str, str]]:
    opts: List[Dict[str, str]] = []
    for o in orders:
        oid = getattr(o, "id", None)
        name = getattr(o, "customer_name", "")
        status = getattr(o, "status", "")
        if oid:
            opts.append({"id": oid, "title": f"{oid} — {name} ({status})"})
    return opts


def _all_variant_options_via_services(db: Session) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    cats = products_service.list_categories(db)
    for c in cats:
        cid = getattr(c, "id", None)
        if not cid:
            continue
        vs = products_service.list_variants_by_category(db, cid)
        items.extend(_map_variants(vs))
    return items


def _format_order_rich_text(order) -> str:
    oid = getattr(order, "id", "")
    status = getattr(order, "status", "")
    created_at = getattr(order, "created_at", "")
    cname = getattr(order, "customer_name", "")
    cphone = getattr(order, "customer_phone", "")
    cemail = getattr(order, "customer_email", "") or ""
    caddr = getattr(order, "customer_address", "") or ""
    fdate = getattr(order, "fulfillment_date", "") or ""
    note = getattr(order, "note", "") or ""

    items = getattr(order, "items", []) or []
    lines = []
    for it in items:
        title = getattr(it, "title", getattr(it, "sku", ""))
        qty = getattr(it, "quantity", 0)
        unit_price = getattr(it, "unit_price", None)
        size = getattr(it, "size", None) or ""
        color = getattr(it, "color", None) or ""
        meta = " ".join([s for s in [size, color] if s]).strip()
        if unit_price is not None:
            line = f"• {title} x {qty} @ ₹{unit_price}"
        else:
            line = f"• {title} x {qty}"
        if meta:
            line += f" ({meta})"
        lines.append(line)

    items_block = "<br/>".join(lines) if lines else "—"
    try:
        total = sum((getattr(it, "unit_price", 0) or 0) * (getattr(it, "quantity", 0) or 0) for it in items)
    except Exception:
        total = 0

    parts = [
        f"<b>Order:</b> {oid} &nbsp; <b>Status:</b> {status}<br/>",
        f"<b>Created:</b> {created_at} &nbsp; <b>Fulfillment:</b> {fdate}<br/><br/>",
        "<b>Customer</b><br/>",
        f"{cname}<br/>{cphone}<br/>{cemail}<br/>{caddr}<br/><br/>",
        f"<b>Items</b><br/>{items_block}<br/><br/>",
        f"<b>Estimated Total:</b> ₹{total}<br/>",
    ]
    if note:
        parts.append(f"<br/><b>Note:</b> {note}")
    return "".join(parts)

# ---------- main flow logic ----------


async def processingDecryptedData_boutique(dd: DecryptedRequestData, db: Session) -> Dict[str, Any]:
    if dd.action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    screen: str = dd.screen or ""
    data_in: Dict[str, Any] = dd.data or {}
    action: Optional[str] = dd.action
    trigger: Optional[str] = (data_in.get("trigger") or "").strip() or None

    # CHOOSE_NAV → hydrate everything
    if screen == "CHOOSE_NAV":
        categories = _map_categories(products_service.list_categories(db))
        items = _all_variant_options_via_services(db)
        all_orders = orders_service.list_orders(db, status=None)
        return {
            "version": "3.0",
            "screen": "CHOOSE_NAV",
            "data": {"categories": categories, "items": items, "orders": _map_orders(all_orders)},
        }

    # VIEW_ORDER
    if screen == "VIEW_ORDER":
        # filter by status
        if action == "data_exchange" and trigger == "filter_by_category":
            status_raw = data_in.get("category") or "ALL"
            status_enum = _status_from_any(status_raw)
            filtered = orders_service.list_orders(db, status_enum)
            return {"version": "3.0", "data": {"orders": _map_orders(filtered)}}

        # select order (no UI change, just acknowledge)
        if action == "data_exchange" and trigger == "select_order":
            return {"version": "3.0", "data": {}}

        # view_order → navigate to details screen
        if action == "data_exchange" and trigger == "view_order":
            order_id = data_in.get("orderId")
            if not order_id:
                return {"version": "3.0", "data": {}}
            try:
                order = orders_service.get_order_out(db, order_id)
                detail = _format_order_rich_text(order)
            except Exception:
                detail = "Unable to load order details."
            return {"version": "3.0", "screen": "VIEW_ORDER_DETAILS", "data": {"order_detail_text": detail}}

        # initial load
        all_orders = orders_service.list_orders(db, status=None)
        return {"version": "3.0", "screen": "VIEW_ORDER", "data": {"orders": _map_orders(all_orders)}}

    # VIEW_ORDER_DETAILS (direct load allowed)
    if screen == "VIEW_ORDER_DETAILS":
        # If you want to re-fetch based on a provided order_id (optional):
        order_id = data_in.get("orderId")
        if order_id:
            try:
                order = orders_service.get_order_out(db, order_id)
                detail = _format_order_rich_text(order)
                return {"version": "3.0", "screen": "VIEW_ORDER_DETAILS", "data": {"order_detail_text": detail}}
            except Exception:
                pass
        # Otherwise, just render whatever data RichText already has
        return {"version": "3.0", "screen": "VIEW_ORDER_DETAILS", "data": data_in}

    # MANAGE_INVENTORY
    if screen == "MANAGE_INVENTORY":
        categories = _map_categories(products_service.list_categories(db))
        items = _all_variant_options_via_services(db)
        return {"version": "3.0", "screen": "MANAGE_INVENTORY", "data": {"categories": categories, "items": items}}

    # Fallback
    return {"version": "3.0", "screen": screen or "CHOOSE_NAV", "data": {}}

# ---------- encrypted endpoint ----------


@router.post("/boutiqueFlow")
async def boutique_flow_handler(
    request: RequestData,
    db: Session = Depends(get_db),
):
    try:
        decryptedDataDict, aes_key, iv = decryptRequest(
            request.encrypted_flow_data,
            request.encrypted_aes_key,
            request.initial_vector,
        )
        decrypted_data = DecryptedRequestData(**decryptedDataDict)
        response_dict = await processingDecryptedData_boutique(decrypted_data, db)
        encrypted_response = encryptResponse(response_dict, aes_key, iv)
        return Response(content=encrypted_response, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

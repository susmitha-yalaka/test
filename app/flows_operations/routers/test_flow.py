# app/routers/test_flow.py
from typing import Any, Dict, Optional, List
import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.encryptDecrypt import (
    DecryptedRequestData,
    RequestData,
    decryptRequest,
    encryptResponse,
)
from app.core.database import get_db
from app.routers import products as products_router
from app.routers import orders as orders_router
from app.models import OrderStatus

router = APIRouter()
log = logging.getLogger("flows.boutique")

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
    print(f"opts{opts}")
    return opts


def _all_variant_options_via_services(db: Session) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    cats = products_router.list_categories(db)
    for c in cats:
        cid = getattr(c, "id", None)
        if not cid:
            continue
        vs = products_router.list_variants_by_category(db, cid)
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
        line = f"• {title} x {qty}" + (f" @ ₹{unit_price}" if unit_price is not None else "")
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
    log.debug("Flow request: action=%s screen=%s", dd.action, dd.screen)

    if dd.action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    screen: str = dd.screen or ""
    data_in: Dict[str, Any] = dd.data or {}
    action: Optional[str] = dd.action
    trigger: Optional[str] = (data_in.get("trigger") or "").strip() or None

    # CHOOSE_NAV → hydrate everything
    if screen == "CHOOSE_NAV":
        categories = _map_categories(products_router.list_categories(db))
        items = _all_variant_options_via_services(db)
        all_orders = orders_router.list_orders(db, status=None)
        log.debug("CHOOSE_NAV hydrated: %d categories, %d items, %d orders",
                  len(categories), len(items), len(all_orders))
        return {
            "version": "3.0",
            "screen": "CHOOSE_NAV",
            "data": {"categories": categories, "items": items, "orders": _map_orders(all_orders),
                      "shipping_status": categories},
        }

    # VIEW_ORDER
    if screen == "VIEW_ORDER":
        log.debug("VIEW_ORDER: action=%s trigger=%s", action, trigger)

        # filter by status
        if action == "data_exchange" and trigger == "apply_filter":
            filters_raw = data_in.get("filter") or "ALL"
            status_enums = [_status_from_any(f) for f in filters_raw]
            print(f"status_enum{status_enums}")
            # Assuming list_orders can accept multiple statuses
            filtered = orders_router.list_orders(db, filters_raw)
            print(f"filtered: {filtered}")

            log.debug("VIEW_ORDER filter: status=%s -> %d orders", filters_raw, len(filtered))

            mapped = _map_orders(filtered)
            print(f"_map_orders(filtered): {mapped}")
            print(f"_map_orders(filtered){_map_orders(filtered)}")
            return {"version": "3.0", "data": {"orders": _map_orders(filtered)}}

        # view_order → navigate to details screen
        if action == "data_exchange" and trigger == "select_order":
            order_id = data_in.get("orderId") or data_in.get("id")
            log.debug("VIEW_ORDER select_order: orderId=%s", order_id)

            if not order_id:
                # nothing selected; keep current screen but return gracefully
                return {"version": "3.0", "screen": "VIEW_ORDER", "data": {}}

            try:
                order = orders_router.get_order(order_id, db)
                detail = _format_order_rich_text(order)
                print(f"detail{detail}")
                return {
                    "version": "3.0",
                    "screen": "VIEW_ORDER_DETAILS",
                    "data": {
                        "order_detail_text": detail
                    },
                }
            except Exception:
                log.exception("Failed to load order details for id=%s", order_id)
                return {
                    "version": "3.0",
                    "screen": "VIEW_ORDER_DETAILS",
                    "data": {"order_detail_text": "Unable to load order details."},
                }

        # initial load
        all_orders = orders_router.list_orders(db, status=None)
        log.debug("VIEW_ORDER initial: %d orders", len(all_orders))
        return {"version": "3.0", "screen": "VIEW_ORDER", "data": {"orders": _map_orders(all_orders)}}

    # VIEW_ORDER_DETAILS (direct load allowed)
    if screen == "VIEW_ORDER_DETAILS":
        order_id = data_in.get("orderId")
        if order_id:
            try:
                order = orders_router.get_order(order_id, db)
                detail = _format_order_rich_text(order)
                return {"version": "3.0", "screen": "VIEW_ORDER_DETAILS", "data": {"order_detail_text": detail}}
            except Exception:
                log.exception("Failed to load order details (direct) for id=%s", order_id)
        return {"version": "3.0", "screen": "VIEW_ORDER_DETAILS", "data": data_in}

    # MANAGE_INVENTORY
    if screen == "MANAGE_INVENTORY":
        categories = _map_categories(products_router.list_categories(db))
        items = _all_variant_options_via_services(db)
        log.debug("MANAGE_INVENTORY hydrated: %d categories, %d items", len(categories), len(items))
        return {"version": "3.0", "screen": "MANAGE_INVENTORY", "data": {"categories": categories, "items": items}}

    # Fallback
    log.debug("Fallback screen: %s", screen)
    return {"version": "3.0", "screen": screen or "CHOOSE_NAV", "data": {}}

# ---------- encrypted endpoint ----------


@router.post("/boutiqueFlow")
async def boutique_flow_handler(
    request: RequestData,
    db: Session = Depends(get_db),
):
    decrypted_data: Optional[DecryptedRequestData] = None
    try:
        decryptedDataDict, aes_key, iv = decryptRequest(
            request.encrypted_flow_data,
            request.encrypted_aes_key,
            request.initial_vector,
        )
        decrypted_data = DecryptedRequestData(**decryptedDataDict)
        print(f"decrypted_data{decrypted_data}")
        log.debug("Decrypted flow: action=%s screen=%s", decrypted_data.action, decrypted_data.screen)

        response_dict = await processingDecryptedData_boutique(decrypted_data, db)
        encrypted_response = encryptResponse(response_dict, aes_key, iv)
        return Response(content=encrypted_response, media_type="application/octet-stream")

    except Exception as e:
        # Log full stack trace to your handlers (file/console), plus helpful context
        log.exception(
            "Flow processing failed: action=%s screen=%s",
            getattr(decrypted_data, "action", None),
            getattr(decrypted_data, "screen", None),
        )
        # Return structured error detail
        tb = traceback.format_exc()
        detail = {
            "error": str(e),
            "exception_type": e.__class__.__name__,
            "screen": getattr(decrypted_data, "screen", None),
            "action": getattr(decrypted_data, "action", None),
            "trace": tb.splitlines()[:2],  # short preview; full trace is in logs
        }
        raise HTTPException(status_code=500, detail=detail)

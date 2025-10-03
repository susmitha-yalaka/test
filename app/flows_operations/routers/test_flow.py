# app/routers/test_flow.py
from datetime import date, datetime
from typing import Any, Dict, Optional, List, Tuple
import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.encryptDecrypt import (
    DecryptedRequestData,
    RequestData,
    decryptRequest,
    encryptResponse,
)
from app.core.database import get_db
from app.routers import orders as orders_router
from app.routers import products as products_router
from app.services import orders as orders_service
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


def _get_str(o: Any, name: str, default: str = "") -> str:
    val = getattr(o, name, default)
    return "" if val is None else str(val)


def _fmt_dt(v: Any) -> str:
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    return _get_str(v, "", "")


def _inr(n: Any) -> str:
    try:
        x = int(n)
    except Exception:
        return "—" if n in (None, "") else f"₹{n}"
    s = str(abs(x))
    if len(s) > 3:
        s = s[:-3][::-1]
        s = ",".join(s[i:i+2] for i in range(0, len(s), 2))[::-1] + "," + str(abs(x))[-3:]
    sign = "-" if x < 0 else ""
    return f"{sign}₹{s}"


def _status_badge(status: str) -> Tuple[str, str]:
    s = (status or "").strip()
    steps = ["Pending", "Confirmed", "Preparing", "Out for delivery", "Delivered"]
    icons = {
        "Pending": "⏳",
        "Confirmed": "🟢",
        "Preparing": "🧑‍🍳",
        "Out for delivery": "🚚",
        "Delivered": "✅",
        "Cancelled": "❌",
    }
    if s == "Cancelled":
        return f"{icons['Cancelled']} Cancelled", "[✖]"
    idx = steps.index(s) if s in steps else 0
    bar = ["●" if i < idx else ("⏺" if i == idx else "○") for i in range(len(steps))]
    return f"{icons.get(s, '⏳')} {s}", "[" + "".join(bar) + "]"


def _format_order_text(o: Any) -> str:
    order_id = _get_str(o, "id")
    status_raw = _get_str(o, "status")
    status_line, status_bar = _status_badge(status_raw)

    created = _fmt_dt(getattr(o, "created_at", None))
    fulfill = _fmt_dt(getattr(o, "fulfillment_date", None))

    cust_name = _get_str(o, "customer_name")
    cust_phone = _get_str(o, "customer_phone")
    cust_email = _get_str(o, "customer_email")
    cust_addr = _get_str(o, "customer_address")

    items = getattr(o, "items", []) or []
    rows: List[Tuple[str, str, str, str]] = []
    total = 0

    for it in items:
        title = _get_str(it, "title") or _get_str(it, "sku")
        size = _get_str(it, "size")
        color = _get_str(it, "color")
        meta = " ".join(p for p in (size, color) if p).strip()
        if meta:
            title = f"{title} ({meta})"

        qty = int(getattr(it, "quantity", 0) or 0)
        unit = getattr(it, "unit_price", None)
        sub = (unit or 0) * qty
        rows.append((title, str(qty), _inr(unit), _inr(sub)))
        total += sub

    # Header
    out: List[str] = []
    header = f"🧾 ORDER {order_id}"
    out.append(header)
    out.append("═" * len(header))
    out.append(f"{status_line}  {status_bar}")
    out.append(f"🕒 Created: {created}")
    out.append(f"📅 Fulfillment: {fulfill}")
    out.append("")

    # Customer
    out.append("👤 CUSTOMER")
    out.append("──────────")
    if cust_name:
        out.append(cust_name)
    if cust_phone:
        out.append(f"📞 {cust_phone}")
    if cust_email:
        out.append(f"✉️  {cust_email}")
    if cust_addr:
        out.append(f"📍 {cust_addr}")
    out.append("")

    # Items block (pseudo-table that reads well on mobile)
    out.append("📦 ITEMS")
    out.append("────────")
    if not rows:
        out.append("—")
    else:
        # compute widths but keep mobile-friendly (cap item width)
        item_w = min(36, max(10, max(len(r[0]) for r in rows)))
        qty_w = max(3, max(len(r[1]) for r in rows))
        unit_w = max(5, max(len(r[2]) for r in rows))
        sub_w = max(7, max(len(r[3]) for r in rows))

        header_row = f"{'Item':<{item_w}} │ {'Qty':^{qty_w}} │ {'Unit':>{unit_w}} │ {'Subtotal':>{sub_w}}"
        out.append(header_row)
        out.append("─" * len(header_row))
        for t, q, u, s in rows:
            out.append(f"{t:<{item_w}} │ {q:^{qty_w}} │ {u:>{unit_w}} │ {s:>{sub_w}}")
        out.append("─" * len(header_row))
        out.append(f"{'TOTAL':<{item_w}} │ {'':^{qty_w}} │ {'':>{unit_w}} │ {_inr(total):>{sub_w}}")

    # Note
    note = _get_str(o, "note")
    if note:
        out.append("")
        out.append("📝 NOTE")
        out.append("──────")
        out.append(note)

    return "\n".join(out)


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
        all_opts = orders_service.orders_list_for_dropdown(db, None)
        orders_payload = jsonable_encoder(all_opts)
        return {
            "version": "3.0",
            "screen": "CHOOSE_NAV",
            "data": {"categories": categories, "items": items, "orders": orders_payload, "shipping_status": categories},
        }

    # VIEW_ORDER
    if screen == "VIEW_ORDER":
        log.debug("VIEW_ORDER: action=%s trigger=%s", action, trigger)

        # filter by status
        if action == "data_exchange" and trigger == "apply_filter":
            filters_raw = data_in.get("filter") or "ALL"
            opts = orders_service.orders_list_for_dropdown(db, filters_raw)
            orders_payload = jsonable_encoder(opts)
            print(f"filtered: {orders_payload}")
            return {"version": "3.0", "data": {"orders": orders_payload}}

        # view_order → navigate to details screen
        if action == "data_exchange" and trigger == "select_order":
            order_id = data_in.get("orderId") or data_in.get("id")
            log.debug("VIEW_ORDER select_order: orderId=%s", order_id)

            if not order_id:
                # nothing selected; keep current screen but return gracefully
                return {"version": "3.0", "screen": "VIEW_ORDER", "data": {}}

            try:
                order = orders_router.get_order(order_id, db)
                detail = _format_order_text(order)
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
                detail = _format_order_text(order)
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

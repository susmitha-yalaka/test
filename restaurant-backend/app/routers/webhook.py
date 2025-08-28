# app/routers/webhook.py

import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.core import config
from app.services.wa import send_text, send_document_by_id, upload_media_pdf
from app.services.menu_service import generate_pdf_if_needed, get_pdf_path

router = APIRouter(prefix="", tags=["webhook"])
log = logging.getLogger("routers.webhook")

_seen_message_ids: Set[str] = set()


@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    print(f"[Webhook][GET] hub_mode={hub_mode}, hub_verify_token={hub_verify_token}")
    if hub_mode == "subscribe" and hub_verify_token == config.VERIFY_TOKEN:
        print("[Webhook][GET] Verification successful")
        return Response(content=hub_challenge or "", media_type="text/plain")
    print("[Webhook][GET] Verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request):
    print("[Webhook][POST] /webhook endpoint hit")

    try:
        body: Dict[str, Any] = await request.json()
        print(f"[Webhook][POST] Full payload: {body}")
    except Exception as e:
        print(f"[Webhook][POST] Failed to parse JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Validate structure
    if "entry" not in body:
        print("[Webhook][POST] Missing 'entry' in payload.")
        raise HTTPException(status_code=400, detail="Missing 'entry' in payload")

    for entry in body.get("entry", []):
        print(f"[Webhook][POST] Entry ID: {entry.get('id')}")
        for change in entry.get("changes", []):
            value: Dict[str, Any] = change.get("value", {})
            print(f"[Webhook][POST] Change keys: {list(value.keys())}")

            # Handle messages
            messages: List[Dict[str, Any]] = value.get("messages", [])
            if not messages:
                print("[Webhook][POST] No messages in this change.")
                continue

            for msg in messages:
                msg_id = msg.get("id")
                if msg_id in _seen_message_ids:
                    print(f"[Webhook][POST] Duplicate message ID: {msg_id} — skipping.")
                    continue
                if msg_id:
                    _seen_message_ids.add(msg_id)

                from_raw = msg.get("from")
                if not from_raw:
                    print("[Webhook][POST] Missing 'from' in message.")
                    continue

                from_number = from_raw if from_raw.startswith("+") else f"+{from_raw}"
                print(f"[Webhook][POST] Incoming message from {from_number}: {msg}")

                # Optional filter
                if config.TARGET_WA_NUMBER and from_number != config.TARGET_WA_NUMBER:
                    print(f"[Webhook][POST] Ignoring number (not target): {from_number}")
                    continue

                # Extract message text
                text = ((msg.get("text") or {}).get("body") or "").strip().lower()
                print(f"[Webhook][POST] Message text: '{text}'")

                # ---- Command Routing ----
                if text == "hi":
                    print("[Webhook][POST] Command matched: hi")
                    await send_text(from_number, config.FLOW_NAME)
                    continue

                if text == "hello":
                    print("[Webhook][POST] Command matched: hello")
                    await send_text(from_number, "Hello! How can we help you today?")
                    continue

                if text == "menu":
                    print("[Webhook][POST] Command matched: menu")
                    try:
                        await generate_pdf_if_needed()
                        pdf_path = str(get_pdf_path())
                        print(f"[Webhook][POST] PDF generated at {pdf_path}")
                    except Exception as e:
                        print(f"[Webhook][POST] PDF generation error: {e}")
                        await send_text(from_number, "⚠️ Sorry, the menu is unavailable right now.")
                        continue

                    ok_upload, media_id_or_err = await upload_media_pdf(pdf_path)
                    print(f"[Webhook][POST] PDF upload result: {ok_upload}, {media_id_or_err}")
                    if not ok_upload:
                        await send_text(from_number, "⚠️ Could not upload the menu right now.")
                        continue

                    ok_send, send_resp = await send_document_by_id(
                        from_number, media_id_or_err, filename="menu.pdf"
                    )
                    print(f"[Webhook][POST] PDF send result: {ok_send}, {send_resp}")
                    if not ok_send:
                        await send_text(from_number, "⚠️ Upload worked but sending the menu failed.")
                    continue

                # ---- Fallback ----
                print("[Webhook][POST] Fallback response triggered")
                await send_text(
                    from_number,
                    "Send *hi* to get the flow name, *hello* to be greeted, or *menu* to receive today’s menu PDF."
                )

    return {"status": "received"}

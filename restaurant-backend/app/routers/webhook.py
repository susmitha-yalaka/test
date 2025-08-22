# app/routers/wa_webhook.py
import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.core import config
from app.services.wa import (
    send_text,
    send_document_by_id,
    upload_media_pdf,
    # send_document_link,  # optional fallback by URL
)
from app.services.menu_service import (
    generate_pdf_if_needed,
    get_pdf_path,
)

router = APIRouter(prefix="", tags=["webhook"])
log = logging.getLogger("routers.webhook")

# simple in-memory idempotency; consider Redis with TTL in production
_seen_message_ids: Set[str] = set()


@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """
    Meta (WhatsApp Cloud API) webhook verification endpoint.
    """
    if hub_mode == "subscribe" and hub_verify_token == config.VERIFY_TOKEN:
        return Response(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request):
    """
    Inbound WhatsApp messages arrive here.
    Commands:
      - "hi"   -> reply with flow name
      - "menu" -> build/refresh local PDF, upload to WhatsApp, send by media_id
    """
    body: Dict[str, Any] = await request.json()

    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value: Dict[str, Any] = change.get("value", {})
                messages: List[Dict[str, Any]] = value.get("messages", [])
                if not messages:
                    continue

                for msg in messages:
                    # idempotency
                    msg_id = msg.get("id")
                    if msg_id and msg_id in _seen_message_ids:
                        continue
                    if msg_id:
                        _seen_message_ids.add(msg_id)

                    from_raw = msg.get("from")
                    if not from_raw:
                        continue
                    from_number = from_raw if from_raw.startswith("+") else f"+{from_raw}"

                    # optional allow-list
                    if config.TARGET_WA_NUMBER and from_number != config.TARGET_WA_NUMBER:
                        continue

                    text = ((msg.get("text") or {}).get("body") or "").strip().lower()

                    # --- command router ---
                    if text == "hi":
                        await send_text(from_number, config.FLOW_NAME)
                        continue

                    if text == "menu":
                        # 1) Ensure we have a fresh/local menu.pdf (build if Excel changed)
                        try:
                            await generate_pdf_if_needed()
                            pdf_path = str(get_pdf_path())
                        except Exception as e:
                            log.exception("Failed generating menu PDF: %s", e)
                            await send_text(from_number, "⚠️ Sorry, the menu is unavailable right now.")
                            continue

                        # 2) Upload the local PDF to WhatsApp media
                        ok_upload, media_id_or_err = await upload_media_pdf(pdf_path)
                        if not ok_upload:
                            log.error("Menu upload failed: %s", media_id_or_err)

                            # Optional fallback to public URL if you expose /menu
                            # link = f"{config.PUBLIC_BASE_URL}/menu"
                            # await send_document_link(to_number=from_number, link=link, filename="menu.pdf")

                            await send_text(from_number, "⚠️ Could not upload the menu right now.")
                            continue

                        # 3) Send the document using media_id
                        ok_send, send_resp = await send_document_by_id(
                            from_number, media_id_or_err, filename="menu.pdf"
                        )
                        if not ok_send:
                            log.error("Menu send failed: %s", send_resp)
                            await send_text(from_number, "⚠️ Upload worked but sending the menu failed.")
                        continue

                    # default help
                    await send_text(
                        from_number,
                        "Send *hi* to get the flow name, or *menu* to receive today’s menu PDF."
                    )

    except Exception as e:
        log.exception("Webhook processing failed: %s", e)

    # Always 200 OK so Meta doesn't retry aggressively
    return {"status": "received"}

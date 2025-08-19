import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.core import config
from ..services.wa import send_document, send_text
from ..utils.security import verify_signature

router = APIRouter(prefix="", tags=["webhook"])
log = logging.getLogger("routers.webhook")


@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == config.VERIFY_TOKEN:
        return Response(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request):
    await verify_signature(request)  # no-op if APP_SECRET not set
    body: Dict[str, Any] = await request.json()
    # log.debug("Incoming webhook: %s", body)

    try:
        # WhatsApp webhook structure: entry[0].changes[0].value.messages[...]
        entries: List[Dict[str, Any]] = body.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])

                for msg in messages:
                    from_number = msg.get("from")  # sender's MSISDN in international format
                    if not from_number:
                        continue

                    # reply with the menu PDF immediately
                    ok_doc, _ = await send_document(
                        to_number=from_number,
                        link=config.MENU_PDF_URL,
                        filename="Restaurant_Menu.pdf",
                    )

                    # optional follow-up
                    if ok_doc and config.SEND_FOLLOWUP and config.FOLLOWUP_TEXT:
                        await send_text(from_number, config.FOLLOWUP_TEXT)

    except Exception as e:
        log.exception("Webhook processing failed: %s", e)

    # Always 200 OK so Meta doesn't retry too aggressively
    return {"status": "received"}

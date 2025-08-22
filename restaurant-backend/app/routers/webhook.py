import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Request

from app.core import config
from ..services.wa import send_document, send_text
# from ..utils.security import verify_signature

router = APIRouter(prefix="", tags=["webhook"])
log = logging.getLogger("routers.webhook")


@router.post("/webhook")
async def receive_webhook(request: Request):
    body: Dict[str, Any] = await request.json()

    try:
        entries: List[Dict[str, Any]] = body.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for msg in messages:
                    from_number_raw = msg.get("from")  # "9198xxxxxxx"
                    if not from_number_raw:
                        continue

                    # normalize to +E.164 for compare
                    from_number = (
                        from_number_raw
                        if from_number_raw.startswith("+")
                        else f"+{from_number_raw}"
                    )

                    # Only react to your specified number
                    if from_number != config.TARGET_WA_NUMBER:
                        continue

                    # message text (text msgs only; ignore buttons, templates, etc.)
                    text = ((msg.get("text") or {}).get("body") or "").strip().lower()

                    if text == "hi":
                        # Reply with the flow name
                        await send_text(from_number, config.FLOW_NAME)
                        # (Optional) stop further processing for this message
                        continue

                    # --- keep your existing behavior below if you still want it ---
                    # e.g., send a PDF menu or a fallback message
                    if getattr(config, "MENU_PDF_URL", None):
                        ok_doc, _ = await send_document(
                            to_number=from_number,
                            link=config.MENU_PDF_URL,
                            filename="Restaurant_Menu.pdf",
                        )
                        if ok_doc and getattr(config, "SEND_FOLLOWUP", False) and getattr(config, "FOLLOWUP_TEXT", ""):
                            await send_text(from_number, config.FOLLOWUP_TEXT)
                    else:
                        await send_text(from_number, "❓ Send *hi* to get the flow name.")

    except Exception as e:
        log.exception("Webhook processing failed: %s", e)

    # Always 200 so Meta doesn't retry too aggressively
    return {"status": "received"}

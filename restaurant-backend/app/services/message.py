import logging
from typing import Dict, Any, Set, List

from app.core import config
from app.services.wa import send_text, send_document_by_id, upload_media_pdf
from app.services.menu_service import generate_pdf_if_needed, get_pdf_path

log = logging.getLogger("services.message_logic")

_seen_message_ids: Set[str] = set()  # in-memory idempotency; swap for Redis in prod


async def handle_webhook_event(body: Dict[str, Any]) -> None:
    """
    Parse the WhatsApp webhook body and send appropriate responses.
    Supports: hi, hello, menu
    """
    print(f"[handle_webhook_event] incoming: {body}")

    entries: List[Dict[str, Any]] = body.get("entry", [])
    if not entries:
        log.warning("Missing 'entry' in payload")
        return

    for entry in entries:
        for change in entry.get("changes", []):
            value: Dict[str, Any] = change.get("value", {})
            messages: List[Dict[str, Any]] = value.get("messages", [])
            if not messages:
                continue

            for msg in messages:
                # idempotency
                msg_id = msg.get("id")
                if msg_id and msg_id in _seen_message_ids:
                    print(f"[handle_webhook_event] duplicate message ignored: {msg_id}")
                    continue
                if msg_id:
                    _seen_message_ids.add(msg_id)

                from_raw = msg.get("from")
                if not from_raw:
                    continue
                from_number = from_raw if from_raw.startswith("+") else f"+{from_raw}"

                # Optional allow-list
                if config.TARGET_WA_NUMBER and from_number != config.TARGET_WA_NUMBER:
                    print(f"[handle_webhook_event] ignoring {from_number} (not TARGET_WA_NUMBER)")
                    continue

                # Only handle text messages for now
                text = ((msg.get("text") or {}).get("body") or "").strip().lower()
                print(f"[handle_webhook_event] from={from_number} text='{text}'")

                if text == "hi":
                    # send configured flow name
                    await send_text(from_number, config.FLOW_NAME)
                    continue

                if text == "hello":
                    await send_text(from_number, "hello, how can we help you?")
                    continue

                if text == "menu":
                    try:
                        # Ensure PDF exists / is fresh
                        await generate_pdf_if_needed()
                        pdf_path = str(get_pdf_path())
                        print(f"[handle_webhook_event] menu pdf at: {pdf_path}")

                        # Upload then send by media_id
                        ok_upload, media_id_or_err = await upload_media_pdf(pdf_path)
                        print(f"[handle_webhook_event] upload ok={ok_upload} result={media_id_or_err}")
                        if not ok_upload:
                            await send_text(from_number, "⚠️ Could not upload the menu right now.")
                            continue

                        ok_send, send_resp = await send_document_by_id(
                            from_number, media_id_or_err, filename="menu.pdf"
                        )
                        print(f"[handle_webhook_event] send ok={ok_send} resp={send_resp}")
                        if not ok_send:
                            await send_text(from_number, "⚠️ Upload worked but sending the menu failed.")
                    except Exception as e:
                        log.exception("PDF generation/send failed: %s", e)
                        await send_text(from_number, "⚠️ Sorry, the menu is not available right now.")
                    continue

                # default fallback
                await send_text(
                    from_number,
                    "Try *hi*, *hello*, or *menu* to explore available options."
                )

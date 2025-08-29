import logging
from typing import Dict, Any
from app.services.wa import send_text, send_document_by_id, upload_media_pdf
from app.services.menu_service import generate_pdf_if_needed, get_pdf_path
log = logging.getLogger("services.message_logic")

_seen_message_ids = set()


async def handle_webhook_event(body: Dict[str, Any]):
    if "entry" not in body:
        log.warning("Missing 'entry' in payload")
        return

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value: Dict[str, Any] = change.get("value", {})

            messages = value.get("messages", [])
            if not messages:
                continue

            for msg in messages:
                msg_id = msg.get("id")
                if msg_id in _seen_message_ids:
                    continue

                _seen_message_ids.add(msg_id)
                from_number = f"+{msg['from']}" if not msg['from'].startswith("+") else msg['from']
                text = ((msg.get("text") or {}).get("body") or "").strip().lower()

                if text == "hi":
                    await send_text(from_number, "Welcome! You've triggered the *hi* flow.")
                elif text == "hello":
                    await send_text(from_number, "👋 Hello! How can we help you?")
                elif text == "menu":
                    try:
                        await generate_pdf_if_needed()
                        pdf_path = str(get_pdf_path())
                        ok_upload, media_id = await upload_media_pdf(pdf_path)
                        if ok_upload:
                            await send_document_by_id(from_number, media_id, filename="menu.pdf")
                        else:
                            await send_text(from_number, "⚠️ Could not upload the menu.")
                    except Exception as e:
                        log.error(f"PDF generation/send failed: {e}")
                        await send_text(from_number, "⚠️ Sorry, the menu is not available.")
                else:
                    await send_text(
                        from_number,
                        "Try *hi*, *hello*, or *menu* to explore available options."
                    )


async def send_response_logic(body: Dict[str, Any]):
    """
    Simulate the deliverContent logic here for testing.
    In practice, use aiohttp or httpx to send requests to the Meta API.
    """
    print("[send_response_logic] This is where you'd send the message via cloud API")
    print(f"Incoming body:\n{body}")

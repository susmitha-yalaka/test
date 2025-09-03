# app/services/message.py
import logging
from typing import Dict, Any, Set

from app.core import config
from app.services.wa import (
    upload_media_pdf,
    send_text,
    send_interactive,
    send_document,
)

from app.services.menu_service import generate_pdf_if_needed, get_pdf_path
from app.services.waiterFlow import waiter_flow  # should return a Pydantic model with .dict()

log = logging.getLogger("services.message_logic")
_seen_message_ids: Set[str] = set()


async def handle_webhook_event(body: Dict[str, Any]) -> None:
    print(f"[handle_webhook_event] incoming: {body}")

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {}) or {}
            messages = value.get("messages", []) or []
            if not messages:
                continue

            for msg in messages:
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
                if getattr(config, "TARGET_WA_NUMBER", "") and from_number != config.TARGET_WA_NUMBER:
                    print(f"[handle_webhook_event] ignoring {from_number} (not TARGET_WA_NUMBER)")
                    continue

                text = ((msg.get("text") or {}).get("body") or "").strip().lower()
                print(f"[handle_webhook_event] from={from_number} text='{text}'")

                if text == "hi":
                    print("inside hi")
                    try:
                        flow_msg = waiter_flow(from_number)
                        payload = flow_msg.dict(exclude_none=True)
                        print(f"flow_msg {payload}")
                        await send_interactive(from_number, payload, msg_id)
                    except Exception as e:
                        log.exception("Failed to send interactive flow: %s", e)
                        await send_text(from_number, getattr(config, "FLOW_NAME", "Flow"), msg_id)
                    continue

                if text == "hello":
                    await send_text(from_number, "hello, how can we help you?", msg_id)
                    continue

                if text == "menu":
                    try:
                        await generate_pdf_if_needed()
                        pdf_path = str(get_pdf_path())
                        print(f"[handle_webhook_event] menu pdf at: {pdf_path}")

                        ok_upload, media_id_or_err = await upload_media_pdf(pdf_path)
                        print(f"[handle_webhook_event] upload ok={ok_upload} result={media_id_or_err}")
                        if not ok_upload:
                            await send_text(from_number, "⚠️ Could not upload the menu right now.", msg_id)
                            continue

                        await send_document(from_number, media_id_or_err, "menu.pdf", msg_id)
                    except Exception as e:
                        log.exception("PDF generation/send failed: %s", e)
                        await send_text(from_number, "⚠️ Sorry, the menu is not available right now.", msg_id)
                    continue

                # default
                await send_text(
                    from_number,
                    "Try *hi*, *hello*, or *menu* to explore available options.",
                    msg_id
                )

# app/services/message.py
import logging
from typing import Dict, Any, Set

from app.core import config
from app.services.wa import send_text, send_document_by_id, upload_media_pdf, send_interactive
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
                    # Build your flow payload via waiter_flow (Pydantic model)
                    try:
                        flow_msg = waiter_flow(from_number)  # should fill flow_id/token/cta/screen etc.
                        ok, resp = await send_interactive(flow_msg.dict())
                        print(f"[handle_webhook_event] flow send ok={ok} resp={resp}")
                        if not ok:
                            # graceful fallback if flow send fails
                            await send_text(from_number, getattr(config, "FLOW_NAME", "Flow"))
                    except Exception as e:
                        log.exception("Failed to send interactive flow: %s", e)
                        await send_text(from_number, getattr(config, "FLOW_NAME", "Flow"))
                    continue

                if text == "hello":
                    await send_text(from_number, "hello, how can we help you?")
                    continue

                if text == "menu":
                    try:
                        await generate_pdf_if_needed()
                        pdf_path = str(get_pdf_path())
                        print(f"[handle_webhook_event] menu pdf at: {pdf_path}")

                        ok_upload, media_id_or_err = await upload_media_pdf(pdf_path)
                        print(f"[handle_webhook_event] upload ok={ok_upload} result={media_id_or_err}")
                        if not ok_upload:
                            await send_text(from_number, "⚠️ Could not upload the menu right now.")
                            continue

                        ok_send, send_resp = await send_document_by_id(from_number, media_id_or_err, filename="menu.pdf")
                        print(f"[handle_webhook_event] send ok={ok_send} resp={send_resp}")
                        if not ok_send:
                            await send_text(from_number, "⚠️ Upload worked but sending the menu failed.")
                    except Exception as e:
                        log.exception("PDF generation/send failed: %s", e)
                        await send_text(from_number, "⚠️ Sorry, the menu is not available right now.")
                    continue

                # default
                await send_text(
                    from_number,
                    "Try *hi*, *hello*, or *menu* to explore available options."
                )

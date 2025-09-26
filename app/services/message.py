# app/services/message.py
import logging
from typing import Any, Dict, Set
from app.core import config
from app.services.handlers import request_handlers
from app.utils.datetime import now_ms_ist, now_str_ist

log = logging.getLogger("services.message_logic")
_seen_message_ids: Set[str] = set()


async def handle_webhook_event(body: Dict[str, Any]) -> None:
    recv_ts = now_ms_ist()
    log.info(f"[RECV] {recv_ts} ms | IST={now_str_ist()}")

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {}) or {}
            for msg in value.get("messages", []) or []:
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
                if getattr(config, "TARGET_WA_NUMBER", "") and from_number != config.TARGET_WA_NUMBER:
                    continue

                # -------- route by WhatsApp message type --------
                msg_type = msg.get("type")
                handler = request_handlers.get(msg_type)
                if not handler:
                    # unknown/unsupported type → ignore or log
                    log.debug(f"Unhandled message type: {msg_type}")
                    continue

                # Pass the whole msg; the type handler decides what to do next
                await handler(msg)

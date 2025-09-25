import asyncio
import os
from typing import Tuple, Union

import httpx

from app.core import config
from app.flows_operations.schema import FlowMessage
from app.utils.datetime import now_ms_ist, now_str_ist

# WhatsApp Graph API endpoints
GRAPH_BASE = f"https://graph.facebook.com/{config.GRAPH_API_VERSION}"
MSG_URL = f"{GRAPH_BASE}/{config.PHONE_NUMBER_ID}/messages"
MEDIA_URL = f"{GRAPH_BASE}/{config.PHONE_NUMBER_ID}/media"

HEADERS_AUTH = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}


def normalize(n: str) -> str:
    """Convert number to E.164 format required by WhatsApp."""
    return n if n.startswith("+") else f"+{n}"


async def _post_to_whatsapp(json_payload: dict) -> Tuple[bool, str]:
    send_initiated_ts = now_ms_ist()
    print(f"[SEND_INITIATED] at {now_str_ist()} ({send_initiated_ts} ms) | to={json_payload.get('to')}")
    """POST payload to WhatsApp messages endpoint."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            MSG_URL,
            headers={**HEADERS_AUTH, "Content-Type": "application/json"},
            json=json_payload,
        )
    send_completed_ts = now_ms_ist()
    print(f"[SEND_COMPLETED] at {now_str_ist()} ({send_completed_ts} ms) | status={r.status_code}")

    return r.status_code < 400, r.text


# ---- Receipts & Indicators ----


def _read_receipt(message_id: str) -> dict:
    """Payload for read receipt."""
    return {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
        "typing_indicator": {
            "type": "text",
        },
    }


async def send_with_receipts(message_id: str, message_payload: dict):
    """
    Send read receipt, typing indicator, and actual message in parallel.
    """
    tasks = [
        _post_to_whatsapp(_read_receipt(message_id)),
        _post_to_whatsapp(message_payload),
    ]
    return await asyncio.gather(*tasks)


# ---- Message Senders ----


async def send_text(to_number: str, body: str, message_id: str) -> Tuple[bool, str]:
    """Send a text message with receipts."""
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize(to_number),
        "type": "text",
        "text": {"body": body},
    }
    return await send_with_receipts(message_id, payload)


async def send_interactive(to_number: str, message: Union[FlowMessage, dict], message_id: str) -> Tuple[bool, str]:
    """Send an interactive message (list, buttons, flow)."""
    if isinstance(message, FlowMessage):
        try:
            payload = message.dict(exclude_none=True)  # Pydantic v1
        except Exception:
            payload = message.model_dump(exclude_none=True)  # Pydantic v2
    else:
        payload = message

    payload["to"] = normalize(to_number)
    return await send_with_receipts(message_id, payload)

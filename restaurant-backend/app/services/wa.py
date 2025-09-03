import asyncio
import os
from typing import Tuple, Union

import httpx
from app.core import config
from app.schema.flow import FlowMessage

# WhatsApp Graph API endpoints
GRAPH_BASE = f"https://graph.facebook.com/{config.GRAPH_API_VERSION}"
MSG_URL = f"{GRAPH_BASE}/{config.PHONE_NUMBER_ID}/messages"
MEDIA_URL = f"{GRAPH_BASE}/{config.PHONE_NUMBER_ID}/media"

HEADERS_AUTH = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}


def normalize(n: str) -> str:
    """Convert number to E.164 format required by WhatsApp."""
    return n if n.startswith("+") else f"+{n}"


async def _post_to_whatsapp(json_payload: dict) -> Tuple[bool, str]:
    """POST payload to WhatsApp messages endpoint."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            MSG_URL,
            headers={**HEADERS_AUTH, "Content-Type": "application/json"},
            json=json_payload,
        )
        return r.status_code < 400, r.text


# ---- Receipts & Indicators ----

def _read_receipt(message_id: str) -> dict:
    """Payload for read receipt."""
    return {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }


def _typing_indicator(to_number: str, state="on") -> dict:
    """Payload for typing indicator (state = 'on' or 'off')."""
    return {
        "messaging_product": "whatsapp",
        "to": normalize(to_number),
        "type": "typing",
        "typing": {"state": state},
    }


async def send_with_receipts(
    to_number: str,
    message_id: str,
    message_payload: dict
):
    """
    Send read receipt, typing indicator, and actual message in parallel.
    """
    tasks = [
        _post_to_whatsapp(_read_receipt(message_id)),
        _post_to_whatsapp(_typing_indicator(to_number, "on")),
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
    return await send_with_receipts(to_number, message_id, payload)


async def send_document(
    to_number: str,
    media_id: str,
    filename: str,
    message_id: str
) -> Tuple[bool, str]:
    """Send a document (already uploaded to WhatsApp)."""
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize(to_number),
        "type": "document",
        "document": {"id": media_id, "filename": filename},
    }
    return await send_with_receipts(to_number, message_id, payload)


async def send_interactive(
    to_number: str,
    message: Union[FlowMessage, dict],
    message_id: str
) -> Tuple[bool, str]:
    """Send an interactive message (list, buttons, flow)."""
    if isinstance(message, FlowMessage):
        try:
            payload = message.dict(exclude_none=True)  # Pydantic v1
        except Exception:
            payload = message.model_dump(exclude_none=True)  # Pydantic v2
    else:
        payload = message

    payload["to"] = normalize(to_number)
    return await send_with_receipts(to_number, message_id, payload)


# ---- Media Upload ----

async def upload_media_pdf(file_path: str) -> Tuple[bool, str]:
    """Upload a local PDF to WhatsApp and return media_id."""
    if not os.path.exists(file_path):
        return False, f"file_not_found:{file_path}"
    if os.path.getsize(file_path) == 0:
        return False, "file_empty"

    files = {
        "file": ("menu.pdf", open(file_path, "rb"), "application/pdf"),
        "type": (None, "application/pdf"),
        "messaging_product": (None, "whatsapp"),
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(MEDIA_URL, headers=HEADERS_AUTH, files=files)
    finally:
        try:
            files["file"][1].close()
        except Exception:
            pass

    if r.status_code < 400:
        return True, r.json().get("id", "")
    return False, r.text

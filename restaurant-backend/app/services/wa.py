import os
from typing import Tuple, Union

import httpx

from app.core import config

# Assuming your Pydantic interfaces live here; adjust if your path differs
from app.schema.flow import (
    FlowMessage,
    Interactive,
    InteractiveBody,
    InteractiveAction,
    InteractiveActionFlowParameters,
    InteractiveActionParametersFlowActionPayload,
    MessagingProduct,
    MessageType,
    RecipientType,
    InteractiveType,
    FlowAction,
)

GRAPH_BASE = f"https://graph.facebook.com/{config.GRAPH_API_VERSION}"
MSG_URL = f"{GRAPH_BASE}/{config.PHONE_NUMBER_ID}/messages"
MEDIA_URL = f"{GRAPH_BASE}/{config.PHONE_NUMBER_ID}/media"

HEADERS_AUTH = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}


def normalize(n: str) -> str:
    """Ensure number is +E.164 format for WhatsApp."""
    return n if n.startswith("+") else f"+{n}"


async def _post_to_whatsapp(json_payload: dict) -> Tuple[bool, str]:
    """Internal helper to POST to WhatsApp messages endpoint."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            MSG_URL,
            headers={**HEADERS_AUTH, "Content-Type": "application/json"},
            json=json_payload,
        )
        return r.status_code < 400, r.text


async def send_text(to_number: str, body: str) -> Tuple[bool, str]:
    """Send a plain text message."""
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize(to_number),
        "type": "text",
        "text": {"body": body},
    }
    return await _post_to_whatsapp(payload)


async def send_document_by_id(
    to_number: str, media_id: str, filename: str = "menu.pdf"
) -> Tuple[bool, str]:
    """Send a document referencing an already-uploaded WhatsApp media_id."""
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize(to_number),
        "type": "document",
        "document": {"id": media_id, "filename": filename},
    }
    return await _post_to_whatsapp(payload)


async def send_document_link(
    to_number: str, link: str, filename: str = "menu.pdf"
) -> Tuple[bool, str]:
    """Send a document by public URL (fallback path)."""
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize(to_number),
        "type": "document",
        "document": {"link": link, "filename": filename},
    }
    return await _post_to_whatsapp(payload)


async def upload_media_pdf(file_path: str) -> Tuple[bool, str]:
    """
    Upload a local PDF to WhatsApp. Returns (ok, media_id_or_error_text).
    WhatsApp Cloud API media limit is ~64 MB.
    """
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
        # always close the file handle
        try:
            files["file"][1].close()
        except Exception:
            pass

    if r.status_code < 400:
        media_id = r.json().get("id", "")
        return True, media_id
    return False, r.text


# ==========================
# WhatsApp Flow: Interactive
# ==========================

async def send_interactive(message: Union[FlowMessage, dict]) -> Tuple[bool, str]:
    """
    Send a WhatsApp Flow (interactive) message using the provided Pydantic model.

    You may pass either a FlowMessage instance or a pre-built dict payload. If a
    FlowMessage instance is provided, it will be serialized to JSON with nulls excluded.
    """
    # print(f"[message]{message}")
    if isinstance(message, FlowMessage):
        # pydantic v1 compatibility
        try:
            payload = message.dict(exclude_none=True)
        except Exception:
            # pydantic v2 fallback (if in use)
            payload = message.model_dump(exclude_none=True)
    else:
        payload = message

    print(f"payload{payload}")

    # As a safety net ensure the phone is normalized if present
    to_number = payload.get("to")
    if isinstance(to_number, str):
        payload["to"] = normalize(to_number)

    return await _post_to_whatsapp(payload)


# ==========================
# Convenience builder (optional)
# ==========================

def build_flow_message(
    *,
    to: str,
    body_text: str,
    flow_token: str,
    flow_id: str,
    flow_cta: str,
    flow_name: str | None = None,
    flow_action: FlowAction = FlowAction.NAVIGATE,
    flow_action_payload: InteractiveActionParametersFlowActionPayload | None = None,
) -> FlowMessage:
    """Construct a strongly-typed FlowMessage ready to be sent via send_interactive()."""
    # Build the action parameters, relying on the Pydantic validator to enforce
    # payload presence/absence based on the selected action.
    params = InteractiveActionFlowParameters(
        flow_message_version="3",
        flow_token=flow_token,
        flow_id=flow_id,
        flow_cta=flow_cta,
        flow_name=flow_name,
        flow_action=flow_action,
        flow_action_payload=flow_action_payload,
    )

    action = InteractiveAction(name="flow", parameters=params)

    interactive = Interactive(
        type=InteractiveType.FLOW,
        body=InteractiveBody(text=body_text),
        action=action,
    )

    msg = FlowMessage(
        messaging_product=MessagingProduct.WHATSAPP,
        recipient_type=RecipientType.INDIVIDUAL,
        to=to,
        type=MessageType.INTERACTIVE,
        interactive=interactive,
    )

    return msg

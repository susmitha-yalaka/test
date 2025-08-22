# app/services/wa.py
import os
from typing import Tuple

import httpx

from app.core import config

GRAPH_BASE = f"https://graph.facebook.com/{config.GRAPH_API_VERSION}"
MSG_URL = f"{GRAPH_BASE}/{config.PHONE_NUMBER_ID}/messages"
MEDIA_URL = f"{GRAPH_BASE}/{config.PHONE_NUMBER_ID}/media"

HEADERS_AUTH = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}


def normalize(n: str) -> str:
    """Ensure number is +E.164 format for WhatsApp."""
    return n if n.startswith("+") else f"+{n}"


async def send_text(to_number: str, body: str) -> Tuple[bool, str]:
    """Send a plain text message."""
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize(to_number),
        "type": "text",
        "text": {"body": body},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            MSG_URL,
            headers={**HEADERS_AUTH, "Content-Type": "application/json"},
            json=payload,
        )
        return r.status_code < 400, r.text


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
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            MSG_URL,
            headers={**HEADERS_AUTH, "Content-Type": "application/json"},
            json=payload,
        )
        return r.status_code < 400, r.text


async def send_document_link(
    to_number: str, link: str, filename: str = "menu.pdf"
) -> Tuple[bool, str]:
    """(Optional) Send a document by public URL (fallback path)."""
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize(to_number),
        "type": "document",
        "document": {"link": link, "filename": filename},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            MSG_URL,
            headers={**HEADERS_AUTH, "Content-Type": "application/json"},
            json=payload,
        )
        return r.status_code < 400, r.text


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

import logging
from typing import Any, Dict, Optional, Tuple

import httpx
from app.core import config

log = logging.getLogger("services.wa")


def graph_messages_url() -> str:
    return f"https://graph.facebook.com/{config.GRAPH_API_VERSION}/{config.PHONE_NUMBER_ID}/messages"


async def _wa_send(payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {config.WABA_TOKEN}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(graph_messages_url(), headers=headers, json=payload)
    ok = 200 <= resp.status_code < 300
    data = resp.json() if resp.content else {}
    log.info("WA send status=%s code=%s resp=%s", "ok" if ok else "err", resp.status_code, data)
    return ok, data


async def send_document(to_number: str, link: str, filename: Optional[str] = None):
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "document",
        "document": {"link": link}
    }
    if filename:
        payload["document"]["filename"] = filename
    return await _wa_send(payload)


async def send_text(to_number: str, body: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body}
    }
    return await _wa_send(payload)

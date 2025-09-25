import asyncio
from typing import Tuple, Union, Dict, Any, List
import json
import logging
import httpx

from app.core import config
from app.flows_operations.schema import FlowMessage
from app.utils.datetime import now_ms_ist, now_str_ist

# WhatsApp Graph API endpoints
GRAPH_BASE = f"https://graph.facebook.com/{config.GRAPH_API_VERSION}"
MSG_URL = f"{GRAPH_BASE}/{config.PHONE_NUMBER_ID}/messages"
MEDIA_URL = f"{GRAPH_BASE}/{config.PHONE_NUMBER_ID}/media"

HEADERS_AUTH: Dict[str, str] = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}

# dedicated logger (configure handlers/rotation at app startup)
logger = logging.getLogger("app.whatsapp")

MASK = "*****"


def normalize(n: str) -> str:
    """Convert number to E.164 format required by WhatsApp."""
    return n if n.startswith("+") else f"+{n}"


def _sanitize_headers(h: Dict[str, str]) -> Dict[str, str]:
    if not h:
        return {}
    out = dict(h)
    for k in list(out.keys()):
        if k.lower() in ("authorization", "x-api-key", "x-auth-token"):
            out[k] = MASK
    return out


def _preview(text: str | bytes | None, limit: int = 4000) -> str:
    if text is None:
        return ""
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8", "replace")
        except Exception:
            return f"<{len(text)} bytes>"
    return text if len(text) <= limit else f"{text[:limit]} …(truncated {len(text)-limit} chars)"


async def _post_to_whatsapp(json_payload: dict) -> Tuple[bool, str]:
    """POST payload to WhatsApp messages endpoint with full logging."""
    to = json_payload.get("to")
    t0 = now_ms_ist()
    logger.info("[SEND_INITIATED] ts=%s to=%s endpoint=%s", now_str_ist(), to, MSG_URL)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20)) as client:
            resp = await client.post(
                MSG_URL,
                headers={**HEADERS_AUTH, "Content-Type": "application/json"},
                json=json_payload,
            )
    except httpx.RequestError as e:
        logger.error("[SEND_FAILED] ts=%s to=%s error=%s", now_str_ist(), to, str(e))
        return False, str(e)

    dt = now_ms_ist() - t0
    reason = getattr(resp, "reason_phrase", "")
    # request context
    try:
        req = resp.request
        logger.info(
            "[REQUEST] %s %s | headers=%s | body=%s",
            req.method,
            str(req.url),
            json.dumps(_sanitize_headers(dict(req.headers)), ensure_ascii=False),
            _preview(getattr(req, "content", b"")),
        )
    except Exception as e:
        logger.debug("Request log failed: %s", e)

    # response context
    logger.info("[SEND_COMPLETED] status=%s reason=%s duration_ms=%s", resp.status_code, reason, dt)
    logger.info("[RESPONSE_HEADERS] %s", json.dumps(dict(resp.headers), ensure_ascii=False))
    logger.info("[RESPONSE_BODY] %s", _preview(resp.text))

    # Parse JSON to extract helpful bits
    body_json: Any = None
    try:
        body_json = resp.json()
    except Exception:
        pass

    if 200 <= resp.status_code < 300:
        msg_id = None
        if isinstance(body_json, dict):
            msgs = body_json.get("messages") or []
            if msgs and isinstance(msgs, list) and isinstance(msgs[0], dict):
                msg_id = msgs[0].get("id")
        logger.info("[WHATSAPP_OK] message_id=%s", msg_id or "<none>")
    else:
        if isinstance(body_json, dict):
            err = body_json.get("error")
            if isinstance(err, dict):
                details = None
                if isinstance(err.get("error_data"), dict):
                    details = err["error_data"].get("details")
                logger.error(
                    "[WHATSAPP_ERROR] message=%r type=%r code=%s subcode=%s details=%r",
                    err.get("message"),
                    err.get("type"),
                    err.get("code"),
                    err.get("error_subcode"),
                    details,
                )

    trace_id = resp.headers.get("x-fb-trace-id") or resp.headers.get("x-fb-debug")
    req_id = resp.headers.get("x-fb-request-id")
    if trace_id or req_id:
        logger.info("[FB_TRACE] trace_id=%s request_id=%s", trace_id, req_id)

    return resp.status_code < 400, resp.text or ""

# ---- Receipts & Send orchestration ----


def _read_receipt(message_id: str) -> dict:
    """Payload for read receipt (Cloud API)."""
    return {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }


async def send_with_receipts(message_id: str, message_payload: dict) -> Tuple[bool, str]:
    """
    Send read receipt + actual message concurrently.
    Return only the message result (ok, text) for call-site simplicity.
    """
    tasks = [
        _post_to_whatsapp(_read_receipt(message_id)),
        _post_to_whatsapp(message_payload),
    ]
    results: List[Tuple[bool, str]] = await asyncio.gather(*tasks, return_exceptions=False)

    # Log receipt result as well
    rr_ok, rr_text = results[0]
    logger.info("[RECEIPT_RESULT] ok=%s body=%s", rr_ok, _preview(rr_text))

    # Return message result to caller
    return results[1]

# ---- Message Senders ----


async def send_text(to_number: str, body: str, message_id: str) -> Tuple[bool, str]:
    payload = {
        "messaging_product": "whatsapp",
        "to": normalize(to_number),
        "type": "text",
        "text": {"body": body},
    }
    return await send_with_receipts(message_id, payload)


async def send_interactive(to_number: str, message: Union[FlowMessage, dict], message_id: str) -> Tuple[bool, str]:
    if isinstance(message, FlowMessage):
        try:
            payload = message.dict(exclude_none=True)  # Pydantic v1
        except Exception:
            payload = message.model_dump(exclude_none=True)  # Pydantic v2
    else:
        payload = message
    payload["to"] = normalize(to_number)
    return await send_with_receipts(message_id, payload)

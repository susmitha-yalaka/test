# app/services/handlers/text.py
from app.services.text_router import route_text


async def handle_text_request(msg: dict) -> None:
    to_number = msg.get("from") or ""
    to_number = to_number if to_number.startswith("+") else f"+{to_number}"
    msg_id = msg.get("id") or ""
    raw_text = ((msg.get("text") or {}).get("body") or "").strip()
    await route_text(to_number, msg_id, raw_text)  # <-- now routed to text_router

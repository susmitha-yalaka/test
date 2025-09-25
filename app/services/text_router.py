# app/services/text_router.py
import re
from typing import Awaitable, Callable, Dict
from app.services.text_handlers import (
    handle_hi, handle_hello, handle_token_flow, handle_fallback
)

TextHandler = Callable[[str, str, str], Awaitable[None]]

COMMANDS: Dict[str, TextHandler] = {
    "hi": handle_hi,
    "hello": handle_hello
}

TOKEN_RX = re.compile(r"#\s*[A-Za-z0-9_\-]+")


async def route_text(to_number: str, msg_id: str, raw_text: str):
    tl = (raw_text or "").strip().lower()
    handler = COMMANDS.get(tl)
    if handler:
        return await handler(to_number, msg_id, raw_text)
    if TOKEN_RX.search(raw_text or ""):
        return await handle_token_flow(to_number, msg_id, raw_text)
    return await handle_fallback(to_number, msg_id, raw_text)

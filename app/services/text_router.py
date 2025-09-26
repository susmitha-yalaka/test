# app/services/text_router.py
from typing import Awaitable, Callable, Dict

from fastapi import Depends
from requests import Session
from app.core.database import get_db
from app.services.text_handlers import (
    handle_hi, handle_hello, handle_fallback
)

TextHandler = Callable[[str, str, str], Awaitable[None]]

COMMANDS: Dict[str, TextHandler] = {
    "hi": handle_hi,
    "hello": handle_hello
}


async def route_text(to_number: str, msg_id: str, raw_text: str, db: Session = Depends(get_db)):
    tl = (raw_text or "").strip().lower()
    handler = COMMANDS.get(tl)
    if handler:
        return await handler(to_number, msg_id, raw_text, db)
    return await handle_fallback(to_number, msg_id, raw_text)

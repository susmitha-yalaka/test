# app/services/text_router.py
from typing import Awaitable, Callable, Dict, Iterator
from contextlib import contextmanager
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.text_handlers import handle_hi, handle_fallback

TextHandler = Callable[[str, str, str, Session], Awaitable[None]]

COMMANDS: Dict[str, TextHandler] = {"hi": handle_hi}


@contextmanager
def db_session() -> Iterator[Session]:
    gen = get_db()
    db = next(gen)
    try:
        yield db
    finally:
        gen.close()


async def route_text(to_number: str, msg_id: str, raw_text: str):
    tl = (raw_text or "").strip().lower()
    handler = COMMANDS.get(tl)
    with db_session() as db:
        if handler:
            return await handler(to_number, msg_id, raw_text, db)
        return await handle_fallback(to_number, msg_id, raw_text)

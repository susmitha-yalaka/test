# app/services/text_handlers.py
import logging

from requests import Session

from app.services.wa import send_text, send_interactive
from app.flows_operations.services.flow_service import seller_flow

log = logging.getLogger(__name__)


async def handle_hi(to: str, msg_id: str, raw_text: str, db: Session) -> None:
    """
    Prefer your interactive 'waiter' flow if available;
    fall back to a simple text if anything fails.
    """
    try:
        flow_msg = seller_flow(to, db)
        payload = flow_msg.dict(exclude_none=True)
        print(f"payload{payload}")
        await send_interactive(to, payload, msg_id)
    except Exception as e:
        log.exception("Failed to send interactive flow: %s", e)
        await send_text(to, "👋 Hi! Send: 'Hi, I am at <Restaurant>, # <token>'", msg_id)


async def handle_hello(to: str, msg_id: str, raw_text: str) -> None:
    await send_text(to, "hello, how can we help you?", msg_id)


async def handle_fallback(to: str, msg_id: str, raw_text: str) -> None:
    await send_text(
        to,
        "Try *hi*, *hello*, *menu*, *login*, or send: 'Hi, I am at <Restaurant>, # <token>'.",
        msg_id,
    )

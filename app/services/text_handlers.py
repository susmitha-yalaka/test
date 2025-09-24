# # app/services/text_handlers.py
# import re
# import logging
# from typing import Optional, Tuple

# from app.services.wa import send_text, send_interactive
# from app.services.menu_pdf import send_menu_pdf
# from app.services.table_service import resolve_table_by_token
# from app.flows_operations.services.flow_service import waiter_flow

# log = logging.getLogger(__name__)

# # ---------- helpers ----------

# _TOKEN_RX = re.compile(r"#\s*([A-Za-z0-9_\-]+)")
# _RESTAURANT_RX = re.compile(r"\bat\s+(.+?)(?:,|#|$)", flags=re.IGNORECASE)


# def _extract_restaurant_and_token(text: str) -> Tuple[Optional[str], Optional[str]]:
#     text = (text or "").strip()
#     m_token = _TOKEN_RX.search(text)
#     token = m_token.group(1) if m_token else None

#     m_rest = _RESTAURANT_RX.search(text)
#     restaurant = m_rest.group(1).strip(" .") if m_rest else None
#     return restaurant, token

# # ---------- intent handlers (called by text_router) ----------


# async def handle_hi(to: str, msg_id: str, raw_text: str) -> None:
#     """
#     Prefer your interactive 'waiter' flow if available;
#     fall back to a simple text if anything fails.
#     """
#     try:
#         flow_msg = waiter_flow(to)
#         payload = flow_msg.dict(exclude_none=True)
#         await send_interactive(to, payload, msg_id)
#     except Exception as e:
#         log.exception("Failed to send interactive flow: %s", e)
#         await send_text(to, "👋 Hi! Send: 'Hi, I am at <Restaurant>, # <token>'", msg_id)


# async def handle_hello(to: str, msg_id: str, raw_text: str) -> None:
#     await send_text(to, "hello, how can we help you?", msg_id)


# async def handle_menu(to: str, msg_id: str, raw_text: str) -> None:
#     await send_menu_pdf(to, msg_id)


# async def handle_login(to: str, msg_id: str, raw_text: str) -> None:
#     await send_text(to, "🪪 Please send: 'Hi, I am at <Restaurant Name>, # <token>'", msg_id)


# async def handle_token_flow(to: str, msg_id: str, raw_text: str) -> None:
#     """
#     Resolve the table from restaurant + token (or token alone),
#     mark it used (commit inside service), greet, then send menu PDF.
#     """
#     restaurant_name, token = _extract_restaurant_and_token(raw_text)
#     if not token:
#         await send_text(to, "⚠️ Please include a valid token after '#'.", msg_id)
#         return

#     try:
#         result = resolve_table_by_token(token=token, restaurant_name=restaurant_name)
#     except Exception as e:
#         log.exception("Table lookup failed: %s", e)
#         await send_text(to, "⚠️ Sorry, something went wrong while checking your table.", msg_id)
#         return

#     if not result:
#         await send_text(to, "❌ I couldn't find a table for that token and restaurant.", msg_id)
#         return

#     friendly_restaurant, table_number = result
#     await send_text(
#         to,
#         f"👋 Welcome to {friendly_restaurant}! "
#         f"You are currently seated at table {table_number}. "
#         f"Please use the menu PDF below.",
#         msg_id,
#     )
#     await send_menu_pdf(to, msg_id)


# async def handle_fallback(to: str, msg_id: str, raw_text: str) -> None:
#     await send_text(
#         to,
#         "Try *hi*, *hello*, *menu*, *login*, or send: 'Hi, I am at <Restaurant>, # <token>'.",
#         msg_id,
#     )

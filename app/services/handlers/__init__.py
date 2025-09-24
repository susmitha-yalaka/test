# app/services/handlers/__init__.py
from typing import Awaitable, Callable, Dict, Optional

from app.services.handlers.text import handle_text_request
from app.services.handlers.button import handle_button_request
from app.services.handlers.location import handle_location_request
from app.services.handlers.interactive import handle_interactive_request

# Signature: handler(message, user) -> Awaitable[Optional[object]]
Handler = Callable[[dict, Optional[dict]], Awaitable[Optional[object]]]

request_handlers: Dict[str, Handler] = {
    "text": handle_text_request,
    "button": handle_button_request,
    "location": handle_location_request,
    "interactive": handle_interactive_request,
}

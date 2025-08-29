import logging
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, HTTPException, Query, Request, Response
from app.core import config
from app.services.message import handle_webhook_event, send_response_logic

router = APIRouter(prefix="", tags=["webhook"])
log = logging.getLogger("routers.webhook")

_seen_message_ids: Set[str] = set()


@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    request: Request = None
):
    print("inside get webhook")
    print(f"[Webhook][GET] hub_mode={hub_mode}, hub_verify_token={hub_verify_token}")
    if hub_mode == "subscribe" and hub_verify_token == config.VERIFY_TOKEN:
        print("[Webhook][GET] Verification successful")
        return Response(content=hub_challenge or "", media_type="text/plain")

    # If not verification, treat as a webhook payload (same as POST)
    try:
        body: Dict[str, Any] = await request.json()
        print("[Webhook][GET] Non-verification event, delegating to logic handler...")
        await handle_webhook_event(body)
        return {"status": "event received"}
    except Exception as e:
        print(f"[Webhook][GET] JSON Parse Error or invalid structure: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook event")


@router.post("/webhook")
async def receive_webhook(request: Request):
    print("[Webhook][POST] /webhook called for sending response")

    try:
        body: Dict[str, Any] = await request.json()
        print("[Webhook][POST] Delegating to message send logic")
        await send_response_logic(body)
        return {"status": "message send processed"}
    except Exception as e:
        print(f"[Webhook][POST] JSON Parse Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook event")

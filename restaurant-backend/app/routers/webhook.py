import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.core import config
from app.services.message import handle_webhook_event

router = APIRouter(prefix="", tags=["webhook"])
log = logging.getLogger("routers.webhook")


@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """
    Meta verification endpoint. Must echo hub.challenge when
    hub.mode=subscribe and verify_token matches.
    """
    print(f"[VERIFY][GET] mode={hub_mode} token_in={hub_verify_token} expected={config.VERIFY_TOKEN}")
    if hub_mode == "subscribe" and hub_verify_token == config.VERIFY_TOKEN:
        print("[VERIFY][GET] success")
        return Response(content=hub_challenge or "", media_type="text/plain")
    print("[VERIFY][GET] failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request):
    """
    WhatsApp Cloud API will POST message events here.
    We delegate to handle_webhook_event which replies (hi/hello/menu).
    """
    try:
        body: Dict[str, Any] = await request.json()
    except Exception as e:
        print(f"[Webhook][POST] JSON parse error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    print("[Webhook][POST] received payload")
    try:
        await handle_webhook_event(body)
    except Exception as e:
        log.exception("Webhook processing failed: %s", e)

    # Always return 200 to prevent excessive retries by Meta
    return {"status": "received"}

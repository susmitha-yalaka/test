from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..services.wa import send_document, send_text

router = APIRouter(prefix="/admin", tags=["admin"])


class SendTestBody(BaseModel):
    to_number: str = Field(..., description="Recipient in international format, e.g. 15551234567")
    type: str = Field("document", pattern="^(document|text)$")
    text: str | None = None
    link: str | None = None
    filename: str | None = None


@router.get("/health")
def health():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}


@router.post("/send-test")
async def send_test(body: SendTestBody):
    if body.type == "text":
        if not body.text:
            raise HTTPException(400, "text is required for type=text")
        ok, data = await send_text(body.to_number, body.text)
        return {"ok": ok, "data": data}

    ok, data = await send_document(
        to_number=body.to_number,
        link=body.link or "https://example.com/menu.pdf",
        filename=body.filename or "Test.pdf",
    )
    return {"ok": ok, "data": data}

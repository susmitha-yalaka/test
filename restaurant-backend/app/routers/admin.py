from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field

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

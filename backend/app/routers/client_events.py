"""Frontend -> backend error reporting, so artifact-rendering failures show up in the
same structured log stream as everything else (event=client_event)."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.logging_utils import get_logger

router = APIRouter(tags=["observability"])
log = get_logger("client")


class ClientEvent(BaseModel):
    type: str = Field(max_length=60)        # e.g. artifact_render_error
    message: str = Field(max_length=500)
    detail: Optional[dict] = None


@router.post("/client-events", status_code=202)
def client_event(ev: ClientEvent):
    log.warning("client_event", extra={"type": ev.type, "message_text": ev.message,
                                       "detail": ev.detail})
    return {"accepted": True}

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=2000)


class PendingConfirmation(BaseModel):
    order_id: str
    action: str
    items: list[dict]
    total_inr: int


class ChatResponse(BaseModel):
    reply_text: str
    ui_state: dict[str, Any]
    pending_confirmation: Optional[PendingConfirmation] = None

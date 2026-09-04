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
    payment_link: Optional[str] = None


class RazorpayEntity(BaseModel):
    """The validated subset of Razorpay webhook entity fields used by this app."""

    id: Optional[str] = None
    reference_id: Optional[str] = None
    notes: dict[str, str] = Field(default_factory=dict)
    error_description: Optional[str] = None


class RazorpayEntityEnvelope(BaseModel):
    entity: RazorpayEntity


class RazorpayWebhookPayload(BaseModel):
    payment_link: Optional[RazorpayEntityEnvelope] = None
    payment: Optional[RazorpayEntityEnvelope] = None


class RazorpayWebhook(BaseModel):
    event: str = Field(min_length=1, max_length=128)
    payload: RazorpayWebhookPayload = Field(default_factory=RazorpayWebhookPayload)

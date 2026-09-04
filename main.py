import json
import os
import time
import traceback
from hmac import compare_digest
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import ValidationError

load_dotenv()

import db
from agent import orchestrator
from agent import policy as policy_module
from models import ChatRequest, ChatResponse, RazorpayWebhook
from tools import razorpay_tools

app = FastAPI(title="Nimbus Gear Checkout Agent", debug=False)

_APP_ENV = os.environ.get("APP_ENV", "development").lower()
_FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "").rstrip("/")
_FRONTEND_PUBLIC_URL = os.environ.get("FRONTEND_PUBLIC_URL", "").rstrip("/")
if _APP_ENV == "production" and (not _FRONTEND_ORIGIN or not _FRONTEND_PUBLIC_URL):
    raise RuntimeError("FRONTEND_ORIGIN and FRONTEND_PUBLIC_URL must be set when APP_ENV=production")

_ALLOWED_ORIGINS = [_FRONTEND_ORIGIN] if _FRONTEND_ORIGIN else ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)

CATALOG_PATH = Path(__file__).parent / "data" / "catalog.json"

db.init_db()

_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 20
_rate_limit_hits = defaultdict(list)


def _check_rate_limit(client_key: str) -> bool:
    now = time.time()
    hits = _rate_limit_hits[client_key]
    hits[:] = [t for t in hits if now - t < _RATE_LIMIT_WINDOW_SECONDS]
    if len(hits) >= _RATE_LIMIT_MAX_REQUESTS:
        return False
    hits.append(now)
    return True


@app.get("/catalog")
def get_catalog():
    with open(CATALOG_PATH) as f:
        return json.load(f)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    client_host = request.client.host if request.client else "unknown"
    if not _check_rate_limit(f"{client_host}:{req.session_id}"):
        raise HTTPException(status_code=429, detail="Too many messages — please slow down.")

    if policy_module.contains_sensitive_message_data(req.message):
        db.log_action(
            req.session_id,
            "chat_turn",
            inputs={"message_length": len(req.message)},
            reasoning="Rejected message containing credentials, payment data, or personal contact information.",
            bound_check_result="rejected: sensitive data is not accepted in chat",
            outcome="rejected",
        )
        raise HTTPException(
            status_code=400,
            detail="For your safety, do not send credentials, card details, or contact information in chat.",
        )

    if db.count_orders_for_session(req.session_id) >= policy_module.MAX_ORDERS_PER_SESSION:
        db.log_action(
            req.session_id,
            "chat_turn",
            inputs={"message_length": len(req.message)},
            reasoning="Session order cap reached.",
            bound_check_result=f"rejected: max {policy_module.MAX_ORDERS_PER_SESSION} orders per session",
            outcome="rejected",
        )
        return ChatResponse(
            reply_text=(
                "This session has reached its order limit for the demo. "
                "Please start a new session to place another order."
            ),
            ui_state={"cart": [], "total_inr": 0},
            pending_confirmation=None,
        )

    try:
        reply_text, ui_state, pending, payment_link = orchestrator.handle_turn(
            req.session_id, req.message
        )
    except Exception as exc:
        # Keep diagnostics in server logs, not in the user-visible audit trail.
        # Provider exceptions can include request data and are not safe audit content.
        traceback.print_exc()
        db.log_action(
            req.session_id,
            "chat_turn",
            inputs={"message_length": len(req.message)},
            reasoning="Agent turn failed safely. Full diagnostic is available only in server logs.",
            outcome="failed",
        )
        raise HTTPException(status_code=500, detail="Something went wrong processing that message.")

    return ChatResponse(
        reply_text=reply_text,
        ui_state=ui_state,
        pending_confirmation=pending,
        payment_link=payment_link,
    )


@app.get("/notifications/{session_id}")
def get_notifications(session_id: str):
    """
    Poll for asynchronous payment status updates (from Razorpay webhooks).
    Returns the notification and marks it as delivered so it doesn't repeat.
    The frontend polls this every few seconds.
    """
    unnotified = db.get_unnotified_order_for_session(session_id)
    if not unnotified:
        return {"notification": None}

    db.update_order(unnotified["order_id"], status_notified=1)

    if unnotified["status"] == "paid":
        # Clear cart and conversation history — the transaction is complete
        db.save_session(session_id, [], None)
        db.save_messages(session_id, [])
        return {
            "notification": {
                "type": "payment_success",
                "order_id": unnotified["order_id"],
                "total_inr": unnotified["total_inr"],
            }
        }

    if unnotified["status"] == "failed":
        return {
            "notification": {
                "type": "payment_failed",
                "order_id": unnotified["order_id"],
                "total_inr": unnotified["total_inr"],
                "reason": unnotified["failure_reason"] or "the payment was declined",
            }
        }

    return {"notification": None}


@app.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

    if not webhook_secret or not razorpay_tools.verify_webhook_signature(
        body.decode("utf-8"), signature, webhook_secret
    ):
        db.log_action(
            None,
            "webhook_received",
            inputs={"signature_present": bool(signature)},
            reasoning="Incoming webhook failed HMAC signature verification.",
            bound_check_result="rejected: invalid signature",
            outcome="rejected",
        )
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        payload = RazorpayWebhook.model_validate_json(body)
    except ValidationError:
        db.log_action(
            None,
            "webhook_received",
            inputs={"payload_bytes": len(body)},
            reasoning="Verified webhook signature but the payload did not match the expected Razorpay event shape.",
            bound_check_result="rejected: malformed webhook payload",
            outcome="rejected",
        )
        raise HTTPException(status_code=400, detail="Malformed webhook payload")

    event = payload.event

    if event == "payment_link.paid":
        payment_link = payload.payload.payment_link
        payment = payload.payload.payment
        if not payment_link or not payment or not payment.entity.id:
            _reject_malformed_webhook(event)
        order_id = payment_link.entity.reference_id
        event_key = f"payment:{payment.entity.id}"
        _apply_webhook_update(
            order_id, event_key, status="paid", razorpay_payment_id=payment.entity.id
        )

    elif event == "payment.failed":
        payment = payload.payload.payment
        if not payment or not payment.entity.id:
            _reject_malformed_webhook(event)
        order_id = payment.entity.notes.get("internal_order_id")
        event_key = f"payment:{payment.entity.id}"
        _apply_webhook_update(
            order_id,
            event_key,
            status="failed",
            razorpay_payment_id=payment.entity.id,
            failure_reason=payment.entity.error_description or "the payment was declined",
        )

    else:
        db.log_action(
            None,
            "webhook_received",
            inputs={"event": event},
            reasoning="Webhook event type not handled by this build.",
            outcome="success",
        )

    return {"status": "ok"}


def _reject_malformed_webhook(event: str):
    db.log_action(
        None,
        "webhook_received",
        inputs={"event": event},
        reasoning="Verified webhook signature but required event data was missing.",
        bound_check_result="rejected: malformed webhook payload",
        outcome="rejected",
    )
    raise HTTPException(status_code=400, detail="Malformed webhook payload")


def _apply_webhook_update(order_id, event_key, **fields):
    order = db.get_order(order_id) if order_id else None
    if not order:
        db.log_action(
            None,
            "webhook_received",
            inputs={"order_id": order_id, "event_key": event_key},
            reasoning="Webhook referenced an unknown order id.",
            bound_check_result="rejected: unknown order",
            outcome="rejected",
        )
        return

    if db.is_event_processed(event_key):
        db.log_action(
            order["session_id"],
            "webhook_received",
            inputs={"event_key": event_key},
            reasoning="Duplicate webhook delivery for an already-processed event; ignored (idempotent).",
            outcome="success",
        )
        return

    if order["status"] == "paid":
        db.mark_event_processed(event_key)
        db.log_action(
            order["session_id"],
            "webhook_received",
            inputs={"event_key": event_key, "attempted_status": fields.get("status")},
            reasoning="Ignored a later webhook because the order was already paid.",
            bound_check_result="rejected: paid is a terminal order state",
            outcome="rejected",
        )
        return

    db.update_order(order_id, status_notified=0, **fields)
    db.mark_event_processed(event_key)
    db.log_action(
        order["session_id"],
        "webhook_received",
        inputs={"event_key": event_key, **fields},
        reasoning="Verified webhook applied to order.",
        bound_check_result="within bounds",
        outcome=fields.get("status", "success"),
    )


@app.get("/audit")
def get_audit(format: str = "json"):
    if format != "json":
        raise HTTPException(status_code=406, detail="Only the safe JSON audit representation is available")
    return JSONResponse(db.get_audit_log())


@app.post("/demo/reset")
def demo_reset(request: Request):
    """
    Wipe all orders, sessions, and audit rows for a clean demo run.
    Call this immediately before presenting — keeps the audit trail tidy.
    """
    reset_token = os.environ.get("DEMO_RESET_TOKEN")
    supplied_token = request.headers.get("X-Demo-Reset-Token", "")
    if not reset_token or not compare_digest(supplied_token, reset_token):
        # Do not reveal whether the endpoint is enabled or the token exists.
        raise HTTPException(status_code=404, detail="Not found")

    db.reset_demo_data()
    _rate_limit_hits.clear()
    return {"status": "ok", "message": "All demo data cleared. Refresh the chat page to start fresh."}


@app.get("/", include_in_schema=False)
def index():
    """Keep FastAPI an API/webhook service; the Next.js app owns browser UI."""
    if _FRONTEND_PUBLIC_URL:
        return RedirectResponse(_FRONTEND_PUBLIC_URL + "/")
    return JSONResponse(
        {
            "service": "Nimbus Gear Checkout API",
            "frontend": "http://localhost:3000",
            "catalog": "/catalog",
            "audit": "/audit",
            "docs": "/docs",
        }
    )

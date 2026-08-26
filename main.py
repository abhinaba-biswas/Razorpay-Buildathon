import json
import os
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

load_dotenv()

import db
from agent import orchestrator
from agent import policy as policy_module
from models import ChatRequest, ChatResponse
from tools import razorpay_tools

app = FastAPI(title="Nimbus Gear Checkout Agent", debug=False)

CATALOG_PATH = Path(__file__).parent / "data" / "catalog.json"
STATIC_DIR = Path(__file__).parent / "static"

db.init_db()

_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 20
_rate_limit_hits = defaultdict(list)


def _check_rate_limit(session_id: str) -> bool:
    now = time.time()
    hits = _rate_limit_hits[session_id]
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
def chat(req: ChatRequest):
    if not _check_rate_limit(req.session_id):
        raise HTTPException(status_code=429, detail="Too many messages — please slow down.")

    if db.count_orders_for_session(req.session_id) >= policy_module.MAX_ORDERS_PER_SESSION:
        db.log_action(
            req.session_id,
            "chat_turn",
            inputs={"message": req.message},
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
        reply_text, ui_state, pending = orchestrator.handle_turn(req.session_id, req.message)
    except Exception:
        db.log_action(
            req.session_id,
            "chat_turn",
            inputs={"message": req.message},
            reasoning="Unhandled error during agent turn.",
            outcome="failed",
        )
        raise HTTPException(status_code=500, detail="Something went wrong processing that message.")

    return ChatResponse(reply_text=reply_text, ui_state=ui_state, pending_confirmation=pending)


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

    payload = json.loads(body)
    event = payload.get("event", "")

    if event == "payment_link.paid":
        entity = payload["payload"]["payment_link"]["entity"]
        payment_entity = payload["payload"]["payment"]["entity"]
        order_id = entity.get("reference_id")
        event_key = f"payment:{payment_entity['id']}"
        _apply_webhook_update(
            order_id, event_key, status="paid", razorpay_payment_id=payment_entity["id"]
        )

    elif event == "payment.failed":
        payment_entity = payload["payload"]["payment"]["entity"]
        order_id = (payment_entity.get("notes") or {}).get("internal_order_id")
        event_key = f"payment:{payment_entity['id']}"
        _apply_webhook_update(
            order_id,
            event_key,
            status="failed",
            razorpay_payment_id=payment_entity["id"],
            failure_reason=payment_entity.get("error_description") or "the payment was declined",
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


def _apply_webhook_update(order_id, event_key, **fields):
    if not order_id or not db.get_order(order_id):
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
            order_id,
            "webhook_received",
            inputs={"event_key": event_key},
            reasoning="Duplicate webhook delivery for an already-processed event; ignored (idempotent).",
            outcome="success",
        )
        return

    db.update_order(order_id, status_notified=0, **fields)
    db.mark_event_processed(event_key)
    db.log_action(
        order_id,
        "webhook_received",
        inputs={"event_key": event_key, **fields},
        reasoning="Verified webhook applied to order.",
        bound_check_result="within bounds",
        outcome=fields.get("status", "success"),
    )


@app.get("/audit")
def get_audit(format: str = "json"):
    rows = db.get_audit_log()
    if format == "html":
        table_rows = "".join(
            f"<tr><td>{r['timestamp']}</td><td>{r['action']}</td>"
            f"<td>{r['reasoning']}</td><td>{r['outcome']}</td></tr>"
            for r in rows
        )
        html = f"<table border='1'><tr><th>Time</th><th>Action</th><th>Reasoning</th><th>Outcome</th></tr>{table_rows}</table>"
        return HTMLResponse(html)
    return JSONResponse(rows)


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "chat.html")

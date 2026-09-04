"""The ONLY module allowed to call Razorpay. The LLM never reaches this code
directly — the orchestrator calls these functions after policy.py validation.
"""

import json
import os
import uuid

import razorpay

import db
from agent import policy

_client = None


def _get_client():
    global _client
    if _client is None:
        key_id = os.environ["RAZORPAY_KEY_ID"]
        key_secret = os.environ["RAZORPAY_KEY_SECRET"]
        _client = razorpay.Client(auth=(key_id, key_secret))
    return _client


def _new_order_id():
    return "order_" + uuid.uuid4().hex[:20]


def create_order(session_id, items):
    """items: list of {"sku_id": str, "qty": int}. Returns a result dict, never raises."""
    ok, resolved_items, total_inr, error = policy.validate_items(items)
    if not ok:
        db.log_action(
            session_id,
            "create_order",
            inputs={"items": items},
            reasoning="Buyer requested a cart; validating against catalog and bounds.",
            bound_check_result=f"rejected: {error}",
            outcome="rejected",
        )
        return {"ok": False, "error": error}

    if db.count_orders_for_session(session_id) >= policy.MAX_ORDERS_PER_SESSION:
        error = f"Session has reached the max of {policy.MAX_ORDERS_PER_SESSION} orders"
        db.log_action(
            session_id,
            "create_order",
            inputs={"items": items},
            reasoning="Buyer requested a cart.",
            bound_check_result=f"rejected: {error}",
            outcome="rejected",
        )
        return {"ok": False, "error": error}

    order_id = _new_order_id()
    requires_confirmation = policy.requires_confirmation(total_inr)

    try:
        client = _get_client()
        rzp_order = client.order.create(
            {
                "amount": total_inr * 100,
                "currency": "INR",
                "receipt": order_id,
                "notes": {"internal_order_id": order_id},
            }
        )
    except Exception:
        db.log_action(
            session_id,
            "create_order",
            inputs={"items": items},
            reasoning="Validated cart, but Razorpay rejected or could not complete the order request.",
            bound_check_result="within bounds",
            outcome="failed",
        )
        return {"ok": False, "error": "Could not create the Razorpay order. Please try again."}

    db.create_order_row(order_id, session_id, resolved_items, total_inr)
    db.update_order(order_id, razorpay_order_id=rzp_order["id"])

    db.log_action(
        session_id,
        "create_order",
        inputs={"items": items},
        reasoning=f"Validated {len(resolved_items)} line item(s) against catalog.json, total ₹{total_inr}.",
        bound_check_result="within bounds" + (", gate required" if requires_confirmation else ""),
        razorpay_response_summary=f"order {rzp_order['id']} status={rzp_order['status']}",
        outcome="success",
    )

    return {
        "ok": True,
        "order_id": order_id,
        "items": resolved_items,
        "total_inr": total_inr,
        "requires_confirmation": requires_confirmation,
    }


def apply_discount(session_id, order_id, pct):
    order = db.get_order(order_id)
    if not order or order["session_id"] != session_id:
        db.log_action(
            session_id,
            "apply_discount",
            inputs={"order_id": order_id, "pct": pct},
            reasoning="Attempted to apply a discount to an order outside this session.",
            bound_check_result="rejected: order not found",
            outcome="rejected",
        )
        return {"ok": False, "error": "Order not found"}

    if order["status"] != "created" or order["razorpay_payment_link_id"]:
        error = "Discounts can only be applied before a payment link is created"
        db.log_action(
            session_id,
            "apply_discount",
            inputs={"order_id": order_id, "pct": pct},
            reasoning="Attempted to change an order after checkout had started.",
            bound_check_result=f"rejected: {error}",
            outcome="rejected",
        )
        return {"ok": False, "error": error}

    ok, error = policy.check_discount(pct, order["total_inr"])
    if not ok:
        db.log_action(
            session_id,
            "apply_discount",
            inputs={"order_id": order_id, "pct": pct},
            reasoning="Buyer or agent requested a discount.",
            bound_check_result=f"rejected: {error}",
            outcome="rejected",
        )
        return {"ok": False, "error": error}

    base_total = sum(i["line_total_inr"] for i in json.loads(order["items_json"]))
    new_total = round(base_total * (100 - pct) / 100)
    if new_total <= 0 or new_total > policy.MAX_ORDER_INR:
        error = f"Discounted total ₹{new_total} is outside the allowed order range"
        db.log_action(
            session_id,
            "apply_discount",
            inputs={"order_id": order_id, "pct": pct},
            reasoning="Calculated discounted total before changing the order.",
            bound_check_result=f"rejected: {error}",
            outcome="rejected",
        )
        return {"ok": False, "error": error}

    db.update_order(order_id, discount_pct=pct, total_inr=new_total)
    db.log_action(
        session_id,
        "apply_discount",
        inputs={"order_id": order_id, "pct": pct},
        reasoning=f"Applied {pct}% discount, within {policy.MAX_DISCOUNT_PCT}% cap.",
        bound_check_result="within bounds",
        outcome="success",
    )
    return {"ok": True, "order_id": order_id, "discount_pct": pct, "total_inr": new_total}


def create_payment_link(session_id, order_id):
    order = db.get_order(order_id)
    if not order or order["session_id"] != session_id:
        db.log_action(
            session_id,
            "create_payment_link",
            inputs={"order_id": order_id},
            reasoning="Attempted to create a payment link.",
            bound_check_result="rejected: order not found",
            outcome="rejected",
        )
        return {"ok": False, "error": "Order not found"}

    if order["razorpay_payment_link_id"]:
        db.log_action(
            session_id,
            "create_payment_link",
            inputs={"order_id": order_id},
            reasoning="Payment link already exists for this order; returning existing link (idempotent).",
            bound_check_result="within bounds",
            outcome="success",
        )
        return {
            "ok": True,
            "order_id": order_id,
            "payment_link_id": order["razorpay_payment_link_id"],
            "short_url": order["razorpay_payment_link_url"] or "",
        }

    items = json.loads(order["items_json"])
    original_cart_total = sum(item["line_total_inr"] for item in items)
    requires_confirmation = policy.requires_confirmation(original_cart_total)
    if requires_confirmation and not order["confirmed"]:
        error = (
            f"Order was created at ₹{original_cart_total}, at/above the ₹{policy.GATE_THRESHOLD_INR} "
            "confirmation gate, and has not been confirmed"
        )
        db.log_action(
            session_id,
            "create_payment_link",
            inputs={"order_id": order_id},
            reasoning="Attempted to create a payment link for a gated order.",
            bound_check_result=f"rejected: {error}",
            outcome="rejected",
        )
        return {"ok": False, "error": error, "requires_confirmation": True}

    description = ", ".join(f"{i['name']} x{i['qty']}" for i in items)[:2048]
    try:
        client = _get_client()
        link = client.payment_link.create(
            {
                "amount": order["total_inr"] * 100,
                "currency": "INR",
                "reference_id": order_id,
                "description": description or f"Order {order_id}",
                "notes": {"internal_order_id": order_id},
                "notify": {"sms": False, "email": False},
            }
        )
    except Exception:
        db.log_action(
            session_id,
            "create_payment_link",
            inputs={"order_id": order_id},
            reasoning="Order was eligible, but Razorpay rejected or could not complete the payment-link request.",
            bound_check_result="within bounds",
            outcome="failed",
        )
        return {"ok": False, "error": "Could not create the Razorpay payment link. Please try again."}

    db.update_order(
        order_id,
        razorpay_payment_link_id=link["id"],
        razorpay_payment_link_url=link["short_url"],
        status="link_created",
    )

    db.log_action(
        session_id,
        "create_payment_link",
        inputs={"order_id": order_id},
        reasoning=(
            f"Order total ₹{order['total_inr']} is "
            f"{'gated and confirmed' if requires_confirmation else 'below the gate'}; creating payment link."
        ),
        bound_check_result="within bounds",
        razorpay_response_summary=f"payment_link {link['id']} status={link['status']}",
        outcome="success",
    )

    return {
        "ok": True,
        "order_id": order_id,
        "payment_link_id": link["id"],
        "short_url": link["short_url"],
    }


def verify_webhook_signature(body: str, signature: str, secret: str) -> bool:
    try:
        _get_client().utility.verify_webhook_signature(body, signature, secret)
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


def get_order_status(session_id, order_id):
    order = db.get_order(order_id)
    if not order or order["session_id"] != session_id:
        return {"ok": False, "error": "Order not found"}
    db.log_action(
        session_id,
        "get_order_status",
        inputs={"order_id": order_id},
        reasoning="Read-only status lookup.",
        bound_check_result="within bounds",
        outcome="success",
    )
    return {
        "ok": True,
        "order_id": order_id,
        "status": order["status"],
        "total_inr": order["total_inr"],
        "confirmed": bool(order["confirmed"]),
    }

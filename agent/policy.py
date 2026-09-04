"""Hard-coded bounds. Imported by tools/razorpay_tools.py and main.py — never by the LLM.

Every constant here is a code-level wall, not a suggestion: raising a limit means
editing this file (and re-testing the gate), not prompting the model differently.
"""

import json
import re
from pathlib import Path

GATE_THRESHOLD_INR = 2000
MAX_ORDER_INR = 10000
MAX_DISCOUNT_PCT = 15
MAX_ORDERS_PER_SESSION = 5
MIN_CART_FOR_DISCOUNT_INR = 2000
MAX_LINE_ITEMS = 10

CATALOG_PATH = Path(__file__).parent.parent / "data" / "catalog.json"

_AFFIRMATIVE_PATTERN_WORDS = {
    "yes",
    "yes confirm",
    "confirm",
    "i confirm",
    "yes, confirm",
    "confirmed",
    "yes please confirm",
}

# This demo never needs credentials, card data, or contact information in chat.
# Rejecting it before it reaches the LLM or persistent conversation history keeps
# the checkout flow deliberately outside PCI/secret-handling scope.
_SENSITIVE_MESSAGE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b", re.IGNORECASE),
    re.compile(r"\b(?:api[_ -]?key|token|password|authorization)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
)


def _load_catalog():
    with open(CATALOG_PATH) as f:
        return json.load(f)


def _catalog_by_id():
    return {item["id"]: item for item in _load_catalog()["items"]}


def validate_items(items):
    """Re-validate every SKU/qty against catalog.json. Never trust LLM-provided price.

    items: list of {"sku_id": str, "qty": int}
    Returns (ok: bool, resolved_items: list, total_inr: int, error: str | None)
    """
    if not isinstance(items, list) or not items:
        return False, [], 0, "Cart must contain at least one item"
    if len(items) > MAX_LINE_ITEMS:
        return False, [], 0, f"Cart cannot contain more than {MAX_LINE_ITEMS} line items"

    catalog = _catalog_by_id()
    quantities_by_sku = {}
    for entry in items:
        if not isinstance(entry, dict):
            return False, [], 0, "Each cart item must be an object"
        sku_id = entry.get("sku_id")
        qty = entry.get("qty")
        if not isinstance(sku_id, str) or sku_id not in catalog:
            return False, [], 0, f"Unknown SKU: {sku_id}"
        # bool is an int subclass in Python, but it is not a valid quantity.
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            return False, [], 0, f"Invalid quantity for {sku_id}: {qty}"
        quantities_by_sku[sku_id] = quantities_by_sku.get(sku_id, 0) + qty

    resolved = []
    total_inr = 0
    for sku_id, qty in quantities_by_sku.items():
        item = catalog[sku_id]
        stock = item.get("stock")
        if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
            return False, [], 0, f"Catalog stock is invalid for {sku_id}"
        if qty > stock:
            return False, [], 0, f"Requested quantity for {sku_id} exceeds available stock ({stock})"
        line_total = item["price_inr"] * qty
        resolved.append(
            {
                "sku_id": sku_id,
                "name": item["name"],
                "qty": qty,
                "unit_price_inr": item["price_inr"],
                "line_total_inr": line_total,
            }
        )
        total_inr += line_total

    if total_inr <= 0:
        return False, [], 0, "Order total must be greater than ₹0"
    if total_inr > MAX_ORDER_INR:
        return False, [], 0, f"Order total ₹{total_inr} exceeds max allowed ₹{MAX_ORDER_INR}"

    return True, resolved, total_inr, None


def requires_confirmation(total_inr):
    return total_inr >= GATE_THRESHOLD_INR


def check_discount(pct, total_inr):
    if isinstance(pct, bool) or not isinstance(pct, int):
        return False, "Discount must be a whole-number percentage"
    if pct < 0:
        return False, "Discount cannot be negative"
    if isinstance(total_inr, bool) or not isinstance(total_inr, int) or total_inr <= 0:
        return False, "Order total is invalid"
    if pct > MAX_DISCOUNT_PCT:
        return False, f"Discount {pct}% exceeds max allowed {MAX_DISCOUNT_PCT}%"
    if total_inr < MIN_CART_FOR_DISCOUNT_INR:
        return False, f"Cart total ₹{total_inr} is below the ₹{MIN_CART_FOR_DISCOUNT_INR} minimum for a discount"
    return True, None


def contains_sensitive_message_data(message: str) -> bool:
    """Return True when user text appears to contain data this checkout must not handle."""
    return any(pattern.search(message) for pattern in _SENSITIVE_MESSAGE_PATTERNS)


def is_explicit_affirmative(message: str) -> bool:
    """Only a distinct, unambiguous affirmative passes the confirmation gate.

    Bare "ok"/"sure"/silence must NOT count — tested adversarially per rules.md §2.
    """
    normalized = message.strip().lower().rstrip(".!")
    return normalized in _AFFIRMATIVE_PATTERN_WORDS

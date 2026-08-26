"""Hard-coded bounds. Imported by tools/razorpay_tools.py and main.py — never by the LLM.

Every constant here is a code-level wall, not a suggestion: raising a limit means
editing this file (and re-testing the gate), not prompting the model differently.
"""

import json
from pathlib import Path

GATE_THRESHOLD_INR = 2000
MAX_ORDER_INR = 10000
MAX_DISCOUNT_PCT = 15
MAX_ORDERS_PER_SESSION = 5
MIN_CART_FOR_DISCOUNT_INR = 2000

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
    catalog = _catalog_by_id()
    resolved = []
    total_inr = 0
    for entry in items:
        sku_id = entry.get("sku_id")
        qty = entry.get("qty", 0)
        if sku_id not in catalog:
            return False, [], 0, f"Unknown SKU: {sku_id}"
        if not isinstance(qty, int) or qty <= 0:
            return False, [], 0, f"Invalid quantity for {sku_id}: {qty}"
        item = catalog[sku_id]
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

    if total_inr > MAX_ORDER_INR:
        return False, [], 0, f"Order total ₹{total_inr} exceeds max allowed ₹{MAX_ORDER_INR}"

    return True, resolved, total_inr, None


def requires_confirmation(total_inr):
    return total_inr >= GATE_THRESHOLD_INR


def check_discount(pct, total_inr):
    if pct > MAX_DISCOUNT_PCT:
        return False, f"Discount {pct}% exceeds max allowed {MAX_DISCOUNT_PCT}%"
    if total_inr < MIN_CART_FOR_DISCOUNT_INR:
        return False, f"Cart total ₹{total_inr} is below the ₹{MIN_CART_FOR_DISCOUNT_INR} minimum for a discount"
    return True, None


def is_explicit_affirmative(message: str) -> bool:
    """Only a distinct, unambiguous affirmative passes the confirmation gate.

    Bare "ok"/"sure"/silence must NOT count — tested adversarially per rules.md §2.
    """
    normalized = message.strip().lower().rstrip(".!")
    return normalized in _AFFIRMATIVE_PATTERN_WORDS

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "audit.db"

_SECRET_KEY_PATTERN = re.compile(r"(secret|token|key|password|authorization)", re.IGNORECASE)

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    items_json TEXT NOT NULL,
    total_inr INTEGER NOT NULL,
    discount_pct INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'created',
    razorpay_order_id TEXT,
    razorpay_payment_link_id TEXT,
    razorpay_payment_link_url TEXT,
    razorpay_payment_id TEXT,
    failure_reason TEXT,
    confirmed INTEGER NOT NULL DEFAULT 0,
    status_notified INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    action TEXT NOT NULL,
    inputs_redacted TEXT,
    reasoning TEXT,
    bound_check_result TEXT,
    razorpay_response_summary TEXT,
    outcome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    cart_json TEXT NOT NULL DEFAULT '[]',
    pending_confirmation_json TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_webhook_events (
    event_key TEXT PRIMARY KEY,
    processed_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def redact(value):
    """Strip any dict key matching a secret/token/key pattern, recursively."""
    if isinstance(value, dict):
        return {
            k: "[REDACTED]" if _SECRET_KEY_PATTERN.search(k) else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def log_action(
    session_id,
    action,
    inputs=None,
    reasoning="",
    bound_check_result="",
    razorpay_response_summary="",
    outcome="success",
):
    redacted_inputs = json.dumps(redact(inputs or {}))
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO audit_log
               (timestamp, session_id, action, inputs_redacted, reasoning,
                bound_check_result, razorpay_response_summary, outcome)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                _now(),
                session_id,
                action,
                redacted_inputs,
                reasoning,
                bound_check_result,
                razorpay_response_summary,
                outcome,
            ),
        )


def get_audit_log(limit=200):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_session(session_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row:
            return {
                "session_id": row["session_id"],
                "cart": json.loads(row["cart_json"]),
                "pending_confirmation": json.loads(row["pending_confirmation_json"])
                if row["pending_confirmation_json"]
                else None,
            }
    return {"session_id": session_id, "cart": [], "pending_confirmation": None}


def save_session(session_id, cart, pending_confirmation):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO sessions (session_id, cart_json, pending_confirmation_json, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 cart_json=excluded.cart_json,
                 pending_confirmation_json=excluded.pending_confirmation_json,
                 updated_at=excluded.updated_at""",
            (
                session_id,
                json.dumps(cart),
                json.dumps(pending_confirmation) if pending_confirmation else None,
                _now(),
            ),
        )


def count_orders_for_session(session_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM orders WHERE session_id = ?", (session_id,)
        ).fetchone()
        return row["c"]


def create_order_row(order_id, session_id, items, total_inr, discount_pct=0):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO orders
               (order_id, session_id, items_json, total_inr, discount_pct, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'created', ?)""",
            (order_id, session_id, json.dumps(items), total_inr, discount_pct, _now()),
        )


def get_order(order_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        return dict(row) if row else None


def update_order(order_id, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [order_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE orders SET {cols} WHERE order_id = ?", values)


def is_event_processed(event_key):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_webhook_events WHERE event_key = ?", (event_key,)
        ).fetchone()
        return row is not None


def mark_event_processed(event_key):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_webhook_events (event_key, processed_at) VALUES (?, ?)",
            (event_key, _now()),
        )


def get_order_by_reference_id(reference_id):
    return get_order(reference_id)


def get_unnotified_order_for_session(session_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM orders
               WHERE session_id = ? AND status_notified = 0
               ORDER BY created_at DESC LIMIT 1""",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None

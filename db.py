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
    messages_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_webhook_events (
    event_key TEXT PRIMARY KEY,
    processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    session_id TEXT PRIMARY KEY,
    history_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
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
    # Safe migration for existing databases that predate the messages_json column
    with get_conn() as conn:
        try:
            conn.execute(
                "ALTER TABLE sessions ADD COLUMN messages_json TEXT NOT NULL DEFAULT '[]'"
            )
        except Exception:
            pass  # Column already present


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


def audit_safe_inputs(inputs):
    """Keep audit data explainable without persisting free-form buyer content."""
    safe = redact(inputs or {})
    if isinstance(safe, dict) and "message" in safe:
        message = safe.pop("message")
        safe["message_length"] = len(message) if isinstance(message, str) else None
    return safe


def log_action(
    session_id,
    action,
    inputs=None,
    reasoning="",
    bound_check_result="",
    razorpay_response_summary="",
    outcome="success",
):
    redacted_inputs = json.dumps(audit_safe_inputs(inputs))
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


def get_audit_log(limit=200, include_sensitive=False):
    with get_conn() as conn:
        columns = (
            "id, timestamp, session_id, action, inputs_redacted, reasoning, "
            "bound_check_result, razorpay_response_summary, outcome"
            if include_sensitive
            else "id, timestamp, action, reasoning, bound_check_result, outcome"
        )
        rows = conn.execute(f"SELECT {columns} FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_session(session_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row:
            keys = row.keys()
            return {
                "session_id": row["session_id"],
                "cart": json.loads(row["cart_json"]),
                "pending_confirmation": json.loads(row["pending_confirmation_json"])
                if row["pending_confirmation_json"]
                else None,
                "messages": json.loads(row["messages_json"])
                if "messages_json" in keys and row["messages_json"]
                else [],
            }
    return {"session_id": session_id, "cart": [], "pending_confirmation": None, "messages": []}


def save_session(session_id, cart, pending_confirmation):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO sessions (session_id, cart_json, pending_confirmation_json, messages_json, updated_at)
               VALUES (?, ?, ?, '[]', ?)
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


def get_messages(session_id) -> list:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT messages_json FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row:
            return json.loads(row["messages_json"] or "[]")
    return []


def save_messages(session_id, messages: list):
    # Keep at most the last 10 messages (5 turns) to avoid token bloat
    trimmed = messages[-10:]
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO sessions (session_id, cart_json, pending_confirmation_json, messages_json, updated_at)
               VALUES (?, '[]', NULL, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 messages_json=excluded.messages_json,
                 updated_at=excluded.updated_at""",
            (session_id, json.dumps(trimmed), _now()),
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


def get_messages(session_id: str) -> list:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT history_json FROM messages WHERE session_id = ?", (session_id,)
        ).fetchone()
        return json.loads(row["history_json"]) if row else []


def save_messages(session_id: str, history: list) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO messages (session_id, history_json, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 history_json=excluded.history_json,
                 updated_at=excluded.updated_at""",
            (session_id, json.dumps(history), _now()),
        )


def reset_demo_data():
    """Wipe all transactional data for a clean demo run. Does not touch catalog."""
    with get_conn() as conn:
        conn.execute("DELETE FROM audit_log")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM processed_webhook_events")

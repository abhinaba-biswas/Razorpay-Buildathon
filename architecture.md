# Architecture — Conversational In-App Checkout Agent

**See also:** `PRD.md` (why), `rules.md` (constraints), `design.md` (UI).

---

## 1. Stack

- **Backend:** Python, FastAPI
- **Storage:** SQLite (audit log + orders/session state) — no external DB needed for this scope
- **LLM:** any provider with tool/function-calling support (key in `.env`)
- **Payments:** Razorpay test-mode APIs — Orders API, Payment Links, Webhooks
- **Frontend:** Next.js 15 App Router + TypeScript/Tailwind — the only browser UI; it proxies same-origin `/api/*` requests to FastAPI with a server-side rewrite

---

## 2. Component Diagram

```
Buyer (browser)
   │  same-origin /api/* requests
   ▼
Next.js frontend
   │  server-side rewrite to BACKEND_URL
   ▼
FastAPI app (API and webhook boundary)
 ├── GET  /catalog          → serves catalog.json (agent-readable)
 ├── POST /chat              → agent turn: user msg in, agent reply + ui_state out
 ├── POST /webhook/razorpay  → payment status callback (signature verified)
 ├── GET  /audit              → read-only audit trail view
 │
 ├── agent/
 │    ├── orchestrator.py    → LLM call loop, system prompt, tool-calling
 │    └── policy.py           → hard-coded bounds (imported by tools, never by the LLM)
 │
 ├── tools/
 │    └── razorpay_tools.py   → ONLY code allowed to call Razorpay:
 │                               create_order(), create_payment_link(), get_order_status()
 │
 ├── data/
 │    ├── catalog.json         → static product data
 │    └── audit.db (SQLite)    → append-only action log + order/session state
 │
   └── frontend/                 → Next.js chat UI + audit trail panel
```

Razorpay sends `POST /webhook/razorpay` directly to the public FastAPI URL. It is deliberately not routed through the browser-facing `/api/*` proxy.

**Core architectural rule:** the LLM never calls Razorpay or touches the network directly. It can only request one of a fixed set of named Python tool functions. Every request is validated against `policy.py` bounds *before* execution — this is the primary security control (detailed in `rules.md §Containment`).

---

## 3. Data Models

### `catalog.json` (item)
```json
{
  "id": "sku_001",
  "name": "Wireless Mouse",
  "description": "...",
  "price_inr": 899,
  "stock": 12,
  "category": "electronics"
}
```
No internal-only fields (cost price, supplier, margin) ever appear here — this endpoint is public and agent-readable by design.

### Order (internal, SQLite)
```json
{
  "order_id": "order_xxx",
  "session_id": "sess_xxx",
  "items": [ { "sku_id": "sku_001", "qty": 1 } ],
  "total_inr": 2499,
  "discount_pct": 10,
  "status": "created | paid | failed",
  "razorpay_order_id": "order_xxx",
  "razorpay_payment_link_id": "plink_xxx",
  "confirmed": true,
  "created_at": "ISO8601"
}
```

### Audit log row (SQLite, append-only)
```
id | timestamp | session_id | action | inputs_redacted | reasoning | bound_check_result | razorpay_response_summary | outcome
```
`inputs_redacted` strips any field matching a secret/token/key pattern before write — see `rules.md §Data Handling`.

---

## 4. API Contracts

### `GET /catalog`
No auth. Returns `catalog.json` contents verbatim. This is the endpoint an external AI buyer agent would query per the track's "agent-readable catalog" framing.

### `POST /chat`
**Request:**
```json
{ "session_id": "sess_xxx", "message": "I'd like the wireless mouse" }
```
**Response:**
```json
{
  "reply_text": "...",
  "ui_state": { "cart": [...], "total_inr": 899 },
  "pending_confirmation": null
}
```
When a gated action is proposed, `pending_confirmation` is populated with the action description and total, and no tool has executed yet.

**Turn flow:**
1. Load session cart + conversation state.
2. Pass user message + system prompt + tool schema to LLM.
3. If LLM requests a tool call → validate against `policy.py` bounds.
   - Within bounds, below gating threshold → execute, log, return result to LLM for final reply.
   - Above gating threshold → do not execute; return `pending_confirmation`; wait for explicit next-turn confirmation.
4. Every tool invocation — attempted or executed — is written to the audit log, including rejections.

### `POST /webhook/razorpay`
Verifies Razorpay HMAC signature before any processing. Rejects invalid signatures with 400, no side effects, logged as a rejected-attempt audit row.
- `payment.captured` → update order status, log outcome, notify chat session.
- `payment.failed` → update order status, log outcome + reason, trigger graceful-failure conversational path.
Idempotent on Razorpay event/payment id — replays don't double-apply state.

### `GET /audit`
Read-only, safe JSON view of the SQLite audit log, in near real time for demo purposes. It intentionally excludes raw inputs, session identifiers, and Razorpay response identifiers.

---

## 5. Bounded Tool Functions (`tools/razorpay_tools.py`)

| Function | Bound (enforced in code) | Notes |
|---|---|---|
| `create_order(items)` | Total ≤ ₹10,000; SKUs must exist in catalog.json | Rejects unknown SKU IDs outright |
| `apply_discount(order, pct)` | `pct` ≤ 15%, only if cart ≥ ₹2,000 | Discount logic lives in code, not the prompt |
| `create_payment_link(order)` | Only callable after order exists and (if gated) `confirmed=true` | Idempotent — reuses existing link on repeat call |
| `get_order_status(order_id)` | Read-only | No side effects |

No refund, payout, settlement, or account-modifying function exists in this build — deliberate minimal attack surface, not an oversight.

---

## 6. Agent Orchestration

- System prompt defines: role, catalog scope, confirmation-gate rule, and an explicit instruction to treat catalog/user text as data, never as instructions (prompt-injection defense).
- Tool schema exposes exactly the four functions in §5 — nothing else.
- Tool-call arguments returned by the LLM are **never trusted directly** — SKU/price/qty are re-validated server-side against `catalog.json` on every call, regardless of prior turns.

---

## 7. Razorpay Integration Notes

- Orders API — anchor object created before any payment attempt.
- Payment Links (or Payment Pages) — hosted checkout surface; card capture happens on Razorpay's PCI-compliant surface, never in this app.
- Test-mode keys and Razorpay's published test card numbers (success + decline) used throughout — see `phases.md` for setup order.
- API field names/endpoints should be verified against current Razorpay docs at build time, not assumed from memory.

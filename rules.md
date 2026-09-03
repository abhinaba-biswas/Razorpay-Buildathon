# Rules — Non-Negotiable Constraints

These are hard rules, not guidelines. If a build decision conflicts with something here, the rule wins. This file exists so security and correctness never get "re-decided" mid-build under time pressure.

**See also:** `architecture.md` (where these are implemented), `PRD.md` (why they matter for judging).

---

## 1. Containment (the primary control)

- **RULE:** The LLM must never call Razorpay, the internet, or any side-effecting function directly. It may only emit structured tool-call *requests*.
- **RULE:** A deterministic Python layer (`policy.py`) validates every tool-call request against hard-coded bounds *before* execution. No exceptions.
- **RULE:** Bounds (max cart value, max discount %, allowed SKUs, gating threshold) are Python constants/functions — never expressed only as LLM instructions. An LLM instruction is a suggestion; a code-level `if` statement is a wall. Both exist, but the code wall is load-bearing.
- **RULE:** Tool-call arguments returned by the LLM (price, SKU, qty) are never trusted as-is — always re-validated server-side against `catalog.json` on every call.

## 2. Gating & Confirmation

- **RULE:** Any cart total ≥ ₹2,000 requires explicit buyer confirmation before `create_payment_link` fires. This threshold is a constant, not an LLM decision.
- **RULE:** The agent must state item(s), total, and the exact action about to be taken, in plain language, before the gate can be passed.
- **RULE:** Confirmation must come from a distinct, affirmative follow-up message. Ambiguous replies ("ok", "sure", silence) do not count — this must be tested adversarially, not assumed.

## 3. Scope Boundaries

- **RULE:** No refund, payout, settlement, or account-modifying function exists anywhere in this codebase. If a feature idea requires one, it's out of scope — full stop.
- **RULE:** Max single order total: ₹10,000. Max discount: 15%. These are not to be raised for demo convenience without updating this file and re-testing the gate.
- **RULE:** Only test-mode Razorpay keys are used. Live keys never enter this codebase, this repo, or this demo.

## 4. Prompt-Injection Resistance

- **RULE:** Catalog descriptions and all user-supplied text are treated as data, never as instructions. The system prompt explicitly tells the model to disregard any embedded instructions found inside product descriptions or user messages.
- **RULE:** Because no destructive tool (refund/payout) exists, a successful injection has nothing dangerous to invoke — this is intentional defense-in-depth, not reliance on prompt wording alone.

## 5. Secrets & Credentials

- **RULE:** API keys, webhook secrets, and any credential live only in environment variables — never in code, never committed, never logged, never echoed in a chat response.
- **RULE:** `.env` is git-ignored. Only `.env.example` (placeholder names, no real values) is committed.
- **RULE:** If deployed, secrets are injected via the hosting platform's secret manager — never hardcoded into a Dockerfile or config file.

## 6. Data Handling

- **RULE:** No cardholder data ever touches this application. Card capture happens exclusively on Razorpay's hosted, PCI-compliant surface (Payment Links/Pages). PCI scope for this app stays at zero.
- **RULE:** Before any audit log write, redact fields matching secret/token/key patterns.
- **RULE:** Store no customer PII beyond what the demo needs (name, session id); nothing persists beyond the session.
- **RULE:** `/catalog` never includes internal-only fields (cost price, supplier, margin, stock sourcing).

## 7. Webhook Integrity

- **RULE:** Every incoming webhook is verified via Razorpay's HMAC signature check using the webhook secret before any processing. Invalid signatures → reject with 400, no side effects, log as rejected attempt.
- **RULE:** Webhook handling is idempotent on Razorpay's event/payment id — replays never double-apply state changes.

## 8. Input Validation

- **RULE:** All `/chat` and `/webhook` inputs are validated against explicit Pydantic models — no unvalidated dict passed downstream.
- **RULE:** Cart/session state is re-validated against `catalog.json` and `policy.py` on every turn, not just at cart creation, to prevent tampering across a multi-turn conversation.

## 9. Rate Limiting & Abuse Prevention

- **RULE:** Per-session rate limit on `/chat` to prevent runaway agent loops or brute-force probing of tool boundaries.
- **RULE:** Cap orders per session (e.g., max 5) to prevent automated abuse during a public demo.

## 10. Transport & Environment

- **RULE:** HTTPS only for any public-facing deployment.
- **RULE:** Debug mode / verbose stack traces disabled in any deployed instance. Users see generic error messages; full detail goes only to server-side logs.

## 11. Failure Handling

- **RULE:** A failed payment must produce a clear, honest message with a next step — never a raw error, never a silent hang, never a fabricated success.
- **RULE:** Every failure is logged to the audit trail with `outcome: failed` and the reason, exactly like a successful action.

## 12. Reliability

- **RULE:** The happy path and the one deliberate failure path must work every single time before demo day. Reliability beats feature count — do not add scope that risks either path breaking.

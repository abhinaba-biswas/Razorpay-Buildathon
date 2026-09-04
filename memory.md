# Memory — Decisions Log & Source of Truth

Purpose: a running record of decisions already made, so they don't get accidentally re-opened or contradicted mid-build (by you, or by an AI coding assistant working from this spec across sessions). If a new decision changes something here, update this file in the same commit.

---

## 1. Locked Decisions

| Decision | Value | Rationale |
|---|---|---|
| Track | Track 01 — AI Growth & Agentic Commerce | Best fit for team's ambition + on-thesis with buildathon's "why now" |
| Direction | Conversational in-app checkout (catalog is supporting infra, not a separate submission) | Catalog alone is too thin a solo demo; checkout is what's visibly judged |
| Team size | Solo | Confirmed by user — full buildathon window, no collaborators |
| Stack | Python + FastAPI, SQLite, vanilla HTML/JS frontend | Fastest path for a solo build, no framework overhead |
| Payments | Razorpay test mode only — Orders API + Payment Links + Webhooks | No live keys, no real money, matches buildathon rules |
| Gating threshold | ₹2,000 | Chosen so demo naturally hits both ungated and gated paths with a small catalog |
| Max discount | 15% | Arbitrary safe ceiling, hard-coded in `policy.py`, not LLM-decided |
| Max single order | ₹10,000 | Keeps blast radius small; no reason to allow more in a demo |
| Refund/payout tools | Explicitly excluded — do not build | Minimizes attack surface; not needed for demo scope |
| Catalog size | 5–10 SKUs | Enough to feel real, small enough to author and QA by hand |
| Audit storage | SQLite, append-only | No need for anything heavier at this scope |
| PCI scope | Zero — card capture happens only on Razorpay's hosted surface | Payment Links/Pages handle this; app never sees card data |
| LLM provider | NVIDIA API (build.nvidia.com/NIM), OpenAI-compatible endpoint, `openai` SDK, model `meta/llama-3.1-70b-instruct` | User's choice; confirmed via docs to support OpenAI-format tool calling. Configurable via `NVIDIA_MODEL` env var. |

---

## 2. Glossary

- **Bounded** — an action whose limits are enforced in code (`policy.py`), not merely instructed to the LLM.
- **Gated** — an action that requires an explicit human confirmation step before execution, triggered above a threshold.
- **Agent-readable catalog** — the `/catalog` JSON endpoint, designed to be queryable by an external AI buyer agent, not just rendered for humans.
- **The Bar** — shorthand for the track's stated judging line: *"Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully."*

---

## 3. Assumptions

- Razorpay's test-mode Orders API, Payment Links, and Webhooks are sufficient to demonstrate the full flow without needing Route, Payouts, or Settlements.
- A single LLM provider with tool-calling support is available and its API key can be obtained before Phase 0 closes.
- The buildathon demo environment allows either a local tunnel (e.g., ngrok) or a quick public deploy for webhook delivery — needs confirming early, since webhooks can't reach `localhost` directly.
- Judges evaluate live or via recorded demo within a 3–5 minute window — pacing decisions in `design.md` assume this.

---

## 4. Open Questions (resolve before Phase 2)

- [x] Confirm current Razorpay test-mode API field names/response shapes against live docs — done during Phase 0–4 scaffolding build; see §7 below for the specific findings (Payment Links API does not accept `order_id`, webhook payload paths, etc.).
- [ ] Decide exact hosting choice for deployment, if demoing from a public URL rather than local.
- [x] Decide LLM provider — NVIDIA API, see §1 above.

---

## 5. Explicitly Rejected Ideas (don't re-propose without new reasoning)

- **Upsell/cross-sell logic** — belongs to a different track direction; adds decision complexity without supporting this track's bar.
- **Campaign orchestration** — same reason, different track direction.
- **Multi-merchant catalog support** — unnecessary scope for a single demo.
- **Storing full customer PII / persistent accounts** — not needed, adds data-handling risk for no demo value.
- **Fancy storefront UI (product photography, carousels)** — time cost without supporting the "agent-readable" thesis; see `design.md §6`.

---

## 6. Confirmed Razorpay API Shapes (verified against live docs + live test-mode calls, 2026-08-26)

- **Payment Links API does not accept an existing `order_id`.** It creates its own internal Razorpay order. Our `create_order()` (Orders API) is our own tracking anchor; the Payment Link is a separate object correlated back via `reference_id` (set to our internal order id) and `notes` (confirmed to propagate into webhook payloads).
- **`payment_link.paid` webhook**: `payload.payment_link.entity.reference_id` is the reliable correlation field.
- **`payment.failed` webhook** (generic, account-level — there is no `payment_link.failed` event): no `reference_id` on this event; correlate via `payload.payment.entity.notes.internal_order_id` instead.
- **Signature header**: `X-Razorpay-Signature`, HMAC-SHA256 hex over the raw body, keyed with the webhook secret — use `razorpay` SDK's `client.utility.verify_webhook_signature(body, signature, secret)`.
- All of the above were exercised against the real Razorpay test-mode API during the Phase 0–4 build (not just doc lookups) — `tools/razorpay_tools.py` and `main.py`'s webhook handler implement this.

## 7. Changelog

| Date | Change |
|---|---|
| Initial spec | PRD, architecture, rules, phases, design, memory files created from planning conversation |
| 2026-08-26 | Phases 0–4 scaffolded: full FastAPI backend (`main.py`, `db.py`, `models.py`), `agent/policy.py` + `agent/orchestrator.py` (NVIDIA API tool-calling loop), `tools/razorpay_tools.py`, `data/catalog.json` (10 SKUs, TrustRail theme), `static/chat.html`. LLM provider decided (NVIDIA). Razorpay API shapes confirmed live — see §6. Gating, bounds, redaction, audit logging, and webhook idempotency all verified end-to-end against the real Razorpay test API. |

*(Add a new row here every time a locked decision changes, rather than editing history silently.)*

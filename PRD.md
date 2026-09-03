# PRD — Conversational In-App Checkout Agent
### Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce

**See also:** `architecture.md` (system design), `rules.md` (constraints/security), `phases.md` (build plan), `design.md` (UI/UX), `memory.md` (decisions log).

---

## 1. Problem Statement

Agent-to-agent and agent-to-human commerce is becoming a live protocol race (NPCI's UAP, ACP, AP2, x402). Merchants today aren't structured for AI buyers or AI-assisted checkout — catalogs are HTML-only, checkout requires manual form-filling, and there's no standard way for an agent to reason about what it's allowed to purchase on a user's behalf.

This project builds a **conversational checkout agent** for a test-mode Razorpay merchant: a buyer chats naturally, the agent understands intent, builds a cart from a machine-readable catalog, and completes payment through Razorpay test APIs — with every money-moving action explainable, bounded, and gated, and a full audit trail of what happened and why.

**Track's own bar (verbatim):** *"Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully."*

---

## 2. Goals

| ID | Goal | Success signal |
|---|---|---|
| G1 | Natural checkout | Buyer completes a purchase via chat, no forms |
| G2 | Agent-readable catalog | Catalog served as structured JSON any agent could query |
| G3 | Zero unbounded actions | No money action executes outside pre-declared limits |
| G4 | Full explainability | Every action has a logged reason, visible to a judge/user |
| G5 | Graceful failure | ≥1 failure path handled without crash or silent error |
| G6 | No security breach | No secret, PII, or unbounded capability is ever exposed or exploitable |

### Non-Goals
- Real payment capture (test mode only)
- Multi-merchant support
- Upsell/cross-sell logic or campaign orchestration (different track directions)
- Refunds, payouts, or settlement flows
- Production-grade scale, multi-currency, or auth/accounts system

---

## 3. Users & Context

- **Primary user (demo persona):** a buyer chatting with a merchant's assistant to purchase 1–3 items from a small catalog.
- **Secondary "user":** an external AI buyer agent that could query `/catalog` programmatically — this is what makes the merchant "transactable by an AI buyer," per the track brief. Not built interactively in v1, but the catalog contract must support it.
- **Judge as user:** needs to see, in a 3–5 minute demo: natural chat checkout → a gated/confirmed high-value action → the audit trail → a handled failure.

---

## 4. Functional Requirements (product level)

1. Buyer can browse a product catalog conversationally and build a cart.
2. Buyer can complete checkout for a cart under a defined threshold with no extra friction.
3. For a cart at/above the threshold, the agent must explain the action and get explicit confirmation before payment is initiated.
4. Every money-moving action is logged with its reasoning and outcome, viewable in an audit trail.
5. If a payment fails, the agent explains why and offers a next step — never a silent failure or fabricated success.
6. The catalog is available as a structured, machine-readable endpoint independent of the chat UI.

Implementation details (tool contracts, data models, endpoints) live in `architecture.md`. Hard constraints (bounds, security) live in `rules.md`.

---

## 5. Success Metrics / Acceptance Criteria

- [ ] End-to-end happy-path purchase completes with a real Razorpay test-mode payment link.
- [ ] At least one purchase in the demo crosses the confirmation-gate threshold and is visibly gated.
- [ ] Ambiguous replies do not count as confirmation (tested adversarially).
- [ ] At least one purchase is deliberately failed (declined test card) and handled gracefully.
- [ ] `/audit` shows reasoning for every action taken, pass or fail.
- [ ] No secret, key, or token ever appears in any UI, log, or response.
- [ ] `/catalog` returns valid structured JSON with no PII or internal-only fields.

---

## 6. Demo Script

1. Cart under threshold → agent completes purchase directly (ungated fast path).
2. Cart at/above threshold → agent explains and pauses → buyer confirms → payment link fires.
3. Cut to `/audit` → walk through logged reasoning for both purchases.
4. Trigger a declined test card → show graceful failure message + audit row.
5. Close on raw `/catalog` JSON — ties back to "transactable by an AI buyer," the track's own framing.

---

## 7. Risks (product-level)

| Risk | Mitigation |
|---|---|
| Demo-day flakiness | Reliability over feature count; rehearse full run twice |
| Judges can't see the "why" | Audit trail is a first-class screen, not a debug afterthought |
| Scope creep (adding upsell/campaign logic) | Explicitly out of scope — see Non-Goals |

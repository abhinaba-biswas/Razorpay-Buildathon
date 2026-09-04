# Design — UI/UX Spec

**See also:** `PRD.md` (what it's for), `architecture.md` (what backs it).

Scope: a single-page Next.js app. Two panels visible at once — this is deliberate, since the audit trail needs to be a first-class, always-visible screen for judges, not a hidden debug view.

---

## 1. Layout

```
┌───────────────────────────────┬───────────────────────┐
│                                  │                          │
│   Chat panel (left, ~65%)        │   Audit trail (right, ~35%)│
│                                  │                          │
│   [conversation history]         │   [live-updating log]     │
│                                  │                          │
│   [cart summary strip]           │                          │
│                                  │                          │
│   [message input]                │                          │
└───────────────────────────────┴───────────────────────┘
```

- Single screen, no navigation, no scrolling between sections — everything relevant to a judge is visible at a glance.
- On narrow/mobile viewports, stack audit trail below chat rather than side-by-side.

---

## 2. Chat Panel

- Standard message bubbles: buyer right-aligned, agent left-aligned.
- A persistent **cart summary strip** above the input, showing current items + running total — this keeps the "state" of the transaction visible without the buyer having to ask.
- Input box + send button. Enter-to-send.
- Typing/thinking indicator while the agent is processing a turn (LLM + tool calls can take a couple seconds — don't let the UI look frozen).

**Tone of agent copy:**
- Plain, direct, transactional — this is a checkout flow, not a chatbot personality showcase. Avoid excessive friendliness/emoji; judges are scoring bounded/gated behavior, not charm.
- Every action the agent is about to take is stated in the message itself before it happens (e.g., "I'll create a payment link for ₹2,499 — confirm?"), never implied.

---

## 3. Confirmation Gate (critical UI moment)

When a cart hits the gating threshold, this must visually read differently from a normal message — it's the single most important interaction in the demo.

- Render the gate as a distinct card/block inside the chat stream (not just plain text), containing:
  - Item(s) and quantities
  - Total amount
  - The exact action about to be taken ("Creating a payment link for ₹X")
  - Two explicit response affordances: a **Confirm** button and a **Cancel/Edit** option
- Buttons exist *in addition to* free-text reply — but per `rules.md`, only an explicit affirmative (button click or clear "yes, confirm") passes the gate. Ambiguous text replies should visibly not trigger the action, and the agent should re-ask.
- While waiting on this gate, no other cart-modifying action is available — the UI should make it clear the conversation is paused on this decision.

---

## 4. Failure State

- Rendered as a distinct, clearly-marked (but not alarming) message block — not a red error banner, not a stack trace, not a generic "something went wrong."
- Structure: what happened → why (if known) → what you can do next (retry / different card).
- Example shape: *"Payment didn't go through — the test card was declined. Want to try again, or use a different card?"*
- This block should visually pair with its corresponding new row appearing in the audit trail, so a judge can watch both update together.

---

## 5. Audit Trail Panel

- Table or card-list, most recent action on top, auto-updating (poll or simple refresh) as actions occur.
- Each row shows, at minimum: timestamp, action name, short reasoning, outcome (success/failed/rejected) — with a clear visual distinction (color or icon) between these three outcomes.
- Clicking a row can optionally expand to show the full logged detail (inputs, Razorpay response summary) — nice-to-have, not required for demo.
- This panel has **no destructive controls** — it's read-only by design, matching `rules.md §7`.

---

## 6. Catalog Surface

- Not necessarily a rendered "shop grid" — the PRD's emphasis is on `/catalog` as a machine-readable endpoint, not a polished storefront.
- For the demo, it's enough to show the raw JSON response in a browser tab or a simple formatted view at the closing beat of the demo script — this reinforces "agent-readable," which is the point, rather than looking like a normal e-commerce page.
- If time allows, a minimal card view of catalog items can appear in the chat's early "browsing" turns, but this is polish, not requirement.

---

## 7. Visual Style

- Dark theme, minimal, high-contrast — consistent with the buildathon site's own aesthetic (dark background, warm accent color for section labels).
- One accent color used consistently for: confirmation-gate cards, "pending" states, and key action buttons — so the eye is drawn to the moments that matter (gating, in particular).
- Typography: one clean sans-serif, no decorative fonts — this is a fintech-adjacent demo, not a consumer lifestyle app.
- Avoid stock e-commerce visual tropes (large product photography, banners, carousels) — they add build time without supporting the track's thesis.

---

## 8. States to Handle Explicitly

| State | UI behavior |
|---|---|
| Idle / browsing | Normal chat, cart strip empty or partial |
| Tool call in progress | Typing/thinking indicator, input disabled |
| Pending confirmation | Gate card rendered, other actions paused |
| Payment link issued | Message with link + "waiting for payment" indicator |
| Payment succeeded | Confirmation message, cart strip clears, audit row appears |
| Payment failed | Graceful failure block, retry offer, audit row appears |
| Rejected tool call (bounds/injection) | Agent explains it can't do that, logged as rejected, no crash |

---

## 9. Accessibility & Copy Notes

- All state changes (gate appearing, payment succeeding/failing) should be conveyed in text, not color/icon alone.
- Keep agent messages short — judges are reading fast during a live demo; dense paragraphs slow the pacing down.

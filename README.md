# Nimbus Gear — Safe Conversational Checkout Agent

Razorpay AI Buildathon submission for **Track 01: AI Growth & Agentic Commerce**.

Nimbus Gear turns a small merchant catalog into a conversational, agent-readable checkout flow. A buyer can describe what they want; the agent resolves only catalog-backed items, applies deterministic policies, creates a Razorpay **test-mode** payment link, and records a safe audit trail.

## Why this is agentic commerce, not just chat

- `GET /catalog` exposes a structured catalog for AI buyers and integrations.
- The LLM can request tools but cannot call Razorpay directly.
- Python policy code, not prompt text, enforces SKU, stock, quantity, order, discount, and confirmation limits.
- A cart at or above ₹2,000 cannot create a payment link until the buyer gives an explicit confirmation.
- Razorpay webhook signatures are verified before payment state is changed.
- The visible audit trail shows the action, reasoning, policy result, and outcome without exposing raw buyer messages or provider identifiers.

## Architecture

```text
Next.js frontend (canonical judge UI)
        │  /api/* rewrite
        ▼
FastAPI policy boundary
 ├── agent/orchestrator.py  LLM tool-call loop
 ├── agent/policy.py        deterministic safety controls
 ├── tools/razorpay_tools.py  only Razorpay boundary
 ├── db.py                  SQLite state + safe audit trail
 └── /catalog               agent-readable merchant data
        │
        ▼
Razorpay test-mode Payment Links + signed webhooks
```

The Next.js app is the only browser frontend. FastAPI serves the API and the signed Razorpay webhook only; it does not serve a duplicate HTML page. In production, configure `FRONTEND_PUBLIC_URL` on FastAPI so its root redirects to the Next.js deployment. In local development, open `http://localhost:3000`; visiting FastAPI directly returns API service metadata.

The frontend calls same-origin `/api/*` paths. The Next.js server-side rewrite forwards every one of those paths to `BACKEND_URL`, keeping the backend host and credentials out of browser code. Configure Razorpay to deliver webhooks directly to `https://your-backend.example/webhook/razorpay`—not through the frontend rewrite.

## Local setup

1. Copy `.env.example` to `.env` and add **test-mode** Razorpay and OpenRouter credentials. Never commit this file.
2. Copy `frontend/.env.example` to `frontend/.env.local` and keep `BACKEND_URL=http://localhost:8000` for local development.
3. Start FastAPI:

   ```bash
   .venv/bin/uvicorn main:app --reload --port 8000
   ```

4. Start the frontend:

   ```bash
   cd frontend && npm ci && npm run dev
   ```

5. Open `http://localhost:3000`.

## Judge demo script

1. **Machine-readable merchant** — open `GET /catalog` and show the structured SKU, price, stock, and category data.
2. **Ungated action** — buy one Wireless Mouse (₹899). Show the created test-mode payment link and a successful audit row.
3. **Bounded, gated action** — buy one Webcam 1080p (₹2,199). Reply `ok` first to show it remains pending, then reply `confirm` to issue the link.
4. **Graceful failure** — complete a Payment Link with Razorpay’s official test failure path. Show the failure card and matching audit entry.
5. **Explainability** — expand an audit row to show the deterministic rule and reason that allowed or rejected the action.

## Safety controls

| Control | Enforced by |
|---|---|
| Catalog-only SKUs and server-derived prices | `agent/policy.py` |
| Non-empty carts, positive integer quantities, stock validation | `agent/policy.py` |
| Max order amount: ₹10,000 | `agent/policy.py` |
| Discount: integer 0–15%, only on eligible pre-checkout orders | `agent/policy.py` and `tools/razorpay_tools.py` |
| Explicit confirmation at ₹2,000+ | `agent/policy.py` and `agent/orchestrator.py` |
| Razorpay calls isolated from the LLM | `tools/razorpay_tools.py` |
| Signed, schema-validated, idempotent webhook updates | `main.py` and `models.py` |
| No credentials, card data, or contact data accepted in chat | `main.py` and `agent/policy.py` |
| Public audit contains only judge-safe fields | `db.py` and `main.py` |
| Destructive reset restricted to a presenter token | `POST /demo/reset` |

## Verification

Run the deterministic regression suite without real Razorpay or LLM network calls:

```bash
.venv/bin/python -m unittest discover -v
```

Run the frontend checks:

```bash
cd frontend
npm ci
npm run build
npx tsc --noEmit
```

See [EVALUATION.md](EVALUATION.md) for the complete acceptance matrix, deployment checklist, and manual evidence required before a live demo.

## Private presenter reset

The reset route is deliberately not exposed in either UI. It is disabled unless `DEMO_RESET_TOKEN` is configured, and requires the matching request header:

```bash
curl -X POST http://localhost:8000/demo/reset \
  -H "X-Demo-Reset-Token: $DEMO_RESET_TOKEN"
```

Use it only immediately before a controlled demo. It clears local SQLite demo data; it does not cancel payment links already created in Razorpay.

# Evaluator Readiness and Release Checklist

This document distinguishes deterministic checks that run in CI from manual checks that require real Razorpay test-mode credentials and a reachable webhook endpoint.

## Automated acceptance matrix

| Requirement | Evidence | Command |
|---|---|---|
| Empty or malformed carts cannot create an order | `tests/test_checkout_security.py` | `.venv/bin/python -m unittest discover -v` |
| Prices, stock, quantities, and ₹10,000 maximum are enforced | `agent/policy.py` plus regression tests | `.venv/bin/python -m unittest discover -v` |
| Negative, non-integer, and >15% discounts are rejected | policy and tool tests | `.venv/bin/python -m unittest discover -v` |
| `ok` and `sure` do not pass the gate; `confirm` does | confirmation test | `.venv/bin/python -m unittest discover -v` |
| Sensitive chat content is rejected before the LLM | API test | `.venv/bin/python -m unittest discover -v` |
| Public audit omits raw inputs and provider identifiers | API test | `.venv/bin/python -m unittest discover -v` |
| Reset cannot be triggered without a presenter token | API test | `.venv/bin/python -m unittest discover -v` |
| Signed webhook payloads are schema-validated and duplicate events are idempotent | webhook test | `.venv/bin/python -m unittest discover -v` |
| Next.js production bundle type-checks and builds | frontend build | `cd frontend && npm ci && npm run build && npx tsc --noEmit` |

## Manual release checklist

Complete every item before presenting. Do not mark a test as passed merely because the code path exists.

- [ ] `APP_ENV=production`, `FRONTEND_ORIGIN`, and `FRONTEND_PUBLIC_URL` are configured on the backend host.
- [ ] Razorpay **test-mode** key ID, secret, and webhook secret are configured through the platform secret manager.
- [ ] `BACKEND_URL` in the Next.js deployment points to the HTTPS FastAPI backend.
- [ ] The configured Razorpay webhook URL is HTTPS and subscribes to `payment_link.paid` and `payment.failed`.
- [ ] An invalid-signature webhook returns 400 and produces no order-state change.
- [ ] An under-threshold cart creates one payment link without a gate.
- [ ] A ₹2,000+ cart displays item names, amount, exact action, and confirm/cancel controls before the link exists.
- [ ] `ok` and `sure` keep the confirmation pending; only an accepted affirmative creates the link.
- [ ] Razorpay’s success test path displays the success state and clears the local cart after the verified webhook.
- [ ] Razorpay’s failure test path displays an honest failure message with a next step and a failed audit entry.
- [ ] The hosted Next.js UI is the only browser frontend; FastAPI exposes only API and webhook routes.
- [ ] Two consecutive clean, timed dry runs are recorded.
- [ ] A screenshot or screen recording is prepared as a contingency; do not use it to claim an unverified live result.

## Deployment contract

### Backend environment

```text
APP_ENV=production
FRONTEND_ORIGIN=https://your-frontend.example
FRONTEND_PUBLIC_URL=https://your-frontend.example
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=openai/gpt-4o-mini
DEMO_RESET_TOKEN=<presenter-only-long-random-value>
```

### Frontend environment

```text
BACKEND_URL=https://your-backend.example
```

`BACKEND_URL` is consumed by the Next.js server-side rewrite. It is intentionally not a browser-exposed `NEXT_PUBLIC_*` variable.

## Payment-link rehearsal hygiene

Razorpay test mode limits the number of Payment Links a business can create. Track created links during rehearsals and avoid wasting them with repeated reset-and-retry loops. The private demo reset clears only local database state; it does not remove a Razorpay Payment Link. See the official [Razorpay Payment Links API documentation](https://razorpay.com/docs/api/payments/payment-links/create-standard/).

## Non-goals retained intentionally

- No live payments.
- No refunds, payouts, settlements, or merchant-account mutations.
- No collection of cardholder data, secrets, or contact information in the application.
- No claim of a real payment result unless it arrived through a verified Razorpay webhook.

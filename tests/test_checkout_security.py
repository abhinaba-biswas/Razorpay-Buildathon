import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import db
import main
from agent import policy
from tools import razorpay_tools


class _FakeOrderAPI:
    def create(self, _payload):
        return {"id": "order_rzp_test", "status": "created"}


class _FakePaymentLinkAPI:
    def create(self, _payload):
        return {
            "id": "plink_rzp_test",
            "short_url": "https://rzp.io/i/test-link",
            "status": "created",
        }


class _FakeUtilityAPI:
    def verify_webhook_signature(self, _body, _signature, _secret):
        return None


class _FakeRazorpayClient:
    order = _FakeOrderAPI()
    payment_link = _FakePaymentLinkAPI()
    utility = _FakeUtilityAPI()


class CheckoutSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = db.DB_PATH
        self.previous_client = razorpay_tools._client
        db.DB_PATH = Path(self.tmp_dir.name) / "audit.db"
        razorpay_tools._client = _FakeRazorpayClient()
        db.init_db()
        main._rate_limit_hits.clear()
        self.client = TestClient(main.app)

    def tearDown(self):
        razorpay_tools._client = self.previous_client
        db.DB_PATH = self.previous_db_path
        self.tmp_dir.cleanup()

    def test_policy_rejects_empty_oversold_and_invalid_discounts(self):
        self.assertFalse(policy.validate_items([])[0])
        self.assertFalse(policy.validate_items([{"sku_id": "sku_001", "qty": 41}])[0])
        self.assertFalse(policy.validate_items([{"sku_id": "sku_001", "qty": True}])[0])
        self.assertFalse(policy.check_discount(-1, 3000)[0])
        self.assertFalse(policy.check_discount("15", 3000)[0])
        self.assertFalse(policy.check_discount(16, 3000)[0])

    def test_duplicate_skus_are_coalesced_before_stock_and_total_checks(self):
        ok, items, total, error = policy.validate_items(
            [{"sku_id": "sku_001", "qty": 1}, {"sku_id": "sku_001", "qty": 2}]
        )
        self.assertTrue(ok, error)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["qty"], 3)
        self.assertEqual(total, 1047)

    def test_confirmation_is_explicit(self):
        self.assertFalse(policy.is_explicit_affirmative("ok"))
        self.assertFalse(policy.is_explicit_affirmative("sure"))
        self.assertTrue(policy.is_explicit_affirmative("confirm"))
        self.assertTrue(policy.is_explicit_affirmative("yes, confirm"))

    def test_sensitive_chat_input_is_rejected_before_llm_processing(self):
        response = self.client.post(
            "/chat",
            json={"session_id": "sess_security", "message": "api_key=sk-abcdefghijklmnopqrst"},
        )
        self.assertEqual(response.status_code, 400)
        audit = db.get_audit_log(include_sensitive=True)
        self.assertEqual(audit[0]["outcome"], "rejected")
        self.assertNotIn("sk-abcdefghijklmnopqrst", audit[0]["inputs_redacted"])

    def test_public_audit_never_returns_raw_inputs_or_provider_details(self):
        db.log_action(
            "sess_audit",
            "chat_turn",
            inputs={"message": "api_key=sk-abcdefghijklmnopqrst"},
            reasoning="Rejected unsafe message.",
            razorpay_response_summary="payment_link plink_private",
            outcome="rejected",
        )
        response = self.client.get("/audit")
        self.assertEqual(response.status_code, 200)
        row = response.json()[0]
        self.assertEqual(
            set(row), {"id", "timestamp", "action", "reasoning", "bound_check_result", "outcome"}
        )
        self.assertNotIn("inputs_redacted", row)
        self.assertNotIn("razorpay_response_summary", row)

    def test_demo_reset_is_not_available_without_presenter_token(self):
        response = self.client.post("/demo/reset")
        self.assertEqual(response.status_code, 404)

    def test_demo_reset_requires_and_honours_presenter_token(self):
        db.log_action("sess_reset", "chat_turn", reasoning="Temporary demo entry.")
        previous_token = os.environ.get("DEMO_RESET_TOKEN")
        os.environ["DEMO_RESET_TOKEN"] = "presenter-test-token"
        try:
            wrong_token = self.client.post(
                "/demo/reset", headers={"X-Demo-Reset-Token": "incorrect"}
            )
            self.assertEqual(wrong_token.status_code, 404)

            reset = self.client.post(
                "/demo/reset", headers={"X-Demo-Reset-Token": "presenter-test-token"}
            )
            self.assertEqual(reset.status_code, 200)
            self.assertEqual(db.get_audit_log(), [])
        finally:
            if previous_token is None:
                os.environ.pop("DEMO_RESET_TOKEN", None)
            else:
                os.environ["DEMO_RESET_TOKEN"] = previous_token

    def test_webhook_validation_and_idempotency(self):
        db.create_order_row("order_webhook", "sess_webhook", [], 349)
        db.update_order("order_webhook", status="link_created")
        payload = {
            "event": "payment_link.paid",
            "payload": {
                "payment_link": {"entity": {"reference_id": "order_webhook"}},
                "payment": {"entity": {"id": "pay_webhook"}},
            },
        }

        previous_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET")
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test-webhook-secret"
        try:
            response = self.client.post(
                "/webhook/razorpay",
                content=json.dumps(payload),
                headers={"X-Razorpay-Signature": "test-signature"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(db.get_order("order_webhook")["status"], "paid")

            duplicate = self.client.post(
                "/webhook/razorpay",
                content=json.dumps(payload),
                headers={"X-Razorpay-Signature": "test-signature"},
            )
            self.assertEqual(duplicate.status_code, 200)
            self.assertEqual(db.get_order("order_webhook")["status"], "paid")

            late_failure = self.client.post(
                "/webhook/razorpay",
                content=json.dumps(
                    {
                        "event": "payment.failed",
                        "payload": {
                            "payment": {
                                "entity": {
                                    "id": "pay_webhook_late_failure",
                                    "notes": {"internal_order_id": "order_webhook"},
                                    "error_description": "declined",
                                }
                            }
                        },
                    }
                ),
                headers={"X-Razorpay-Signature": "test-signature"},
            )
            self.assertEqual(late_failure.status_code, 200)
            self.assertEqual(db.get_order("order_webhook")["status"], "paid")

            malformed = self.client.post(
                "/webhook/razorpay",
                content=json.dumps({"event": "payment_link.paid", "payload": {}}),
                headers={"X-Razorpay-Signature": "test-signature"},
            )
            self.assertEqual(malformed.status_code, 400)

            db.create_order_row("order_failed", "sess_failed", [], 349)
            db.update_order("order_failed", status="link_created")
            failed = self.client.post(
                "/webhook/razorpay",
                content=json.dumps(
                    {
                        "event": "payment.failed",
                        "payload": {
                            "payment": {
                                "entity": {
                                    "id": "pay_failed",
                                    "notes": {"internal_order_id": "order_failed"},
                                    "error_description": "declined test payment",
                                }
                            }
                        },
                    }
                ),
                headers={"X-Razorpay-Signature": "test-signature"},
            )
            self.assertEqual(failed.status_code, 200)
            self.assertEqual(db.get_order("order_failed")["status"], "failed")
            notification = self.client.get("/notifications/sess_failed").json()["notification"]
            self.assertEqual(notification["type"], "payment_failed")
        finally:
            if previous_secret is None:
                os.environ.pop("RAZORPAY_WEBHOOK_SECRET", None)
            else:
                os.environ["RAZORPAY_WEBHOOK_SECRET"] = previous_secret

    def test_razorpay_requests_are_bounded_and_errors_are_audited(self):
        invalid = razorpay_tools.create_order("sess_tools", [])
        self.assertFalse(invalid["ok"])

        created = razorpay_tools.create_order("sess_tools", [{"sku_id": "sku_003", "qty": 1}])
        self.assertTrue(created["ok"])
        self.assertEqual(created["total_inr"], 899)

        negative_discount = razorpay_tools.apply_discount("sess_tools", created["order_id"], -1)
        self.assertFalse(negative_discount["ok"])

        payment_link = razorpay_tools.create_payment_link("sess_tools", created["order_id"])
        self.assertTrue(payment_link["ok"])
        late_discount = razorpay_tools.apply_discount("sess_tools", created["order_id"], 10)
        self.assertFalse(late_discount["ok"])

        gated = razorpay_tools.create_order("sess_tools", [{"sku_id": "sku_008", "qty": 1}])
        self.assertTrue(gated["requires_confirmation"])
        discounted = razorpay_tools.apply_discount("sess_tools", gated["order_id"], 15)
        self.assertTrue(discounted["ok"])
        self.assertLess(discounted["total_inr"], policy.GATE_THRESHOLD_INR)
        still_gated = razorpay_tools.create_payment_link("sess_tools", gated["order_id"])
        self.assertFalse(still_gated["ok"])
        self.assertTrue(still_gated["requires_confirmation"])


if __name__ == "__main__":
    unittest.main()

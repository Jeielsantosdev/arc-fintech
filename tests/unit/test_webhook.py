"""Unit tests for webhook dispatcher signature verification."""

import json
import time

from src.infrastructure.webhooks.dispatcher import WebhookDispatcher, _sign_payload


class TestWebhookSignature:
    SECRET = "test-secret-key"

    def test_sign_and_verify(self):
        body = json.dumps({"event": "payment.confirmed", "data": {}})
        signature = _sign_payload(body, self.SECRET)
        assert WebhookDispatcher.verify_signature(body, signature, self.SECRET)

    def test_wrong_secret_fails(self):
        body = json.dumps({"event": "test"})
        signature = _sign_payload(body, self.SECRET)
        assert not WebhookDispatcher.verify_signature(body, signature, "wrong-secret")

    def test_tampered_body_fails(self):
        body = json.dumps({"event": "test"})
        signature = _sign_payload(body, self.SECRET)
        tampered = json.dumps({"event": "injected"})
        assert not WebhookDispatcher.verify_signature(tampered, signature, self.SECRET)

    def test_malformed_signature_returns_false(self):
        assert not WebhookDispatcher.verify_signature("body", "malformed", self.SECRET)

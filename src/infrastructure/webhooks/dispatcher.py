"""Webhook dispatcher with HMAC-SHA256 signature and retry logic."""

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

logger = logging.getLogger(__name__)


def _sign_payload(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature: t={ts},v1={hex}."""
    ts = str(int(time.time()))
    signed = f"{ts}.{payload}"
    sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


class WebhookDispatcher:
    """
    Delivers event payloads to customer webhook URLs.

    Signs every request with HMAC-SHA256 so recipients can verify authenticity.
    Retries up to 3 times with exponential backoff.
    """

    def __init__(self, secret: str | None = None, timeout: int | None = None) -> None:
        self._secret = secret or settings.webhook_secret
        self._timeout = timeout or settings.webhook_timeout

    def _build_payload(self, event_type: str, data: dict) -> dict:
        return {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _post(self, url: str, payload: dict) -> None:
        body = json.dumps(payload, default=str)
        signature = _sign_payload(body, self._secret)
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Arc-Signature": signature,
                    "X-Arc-Event": payload["event"],
                },
            )
            resp.raise_for_status()

    def send(self, url: str, event_type: str, data: dict) -> bool:
        """
        Dispatch a webhook event. Returns True on success, False on failure.
        """
        payload = self._build_payload(event_type, data)
        try:
            self._post(url, payload)
            logger.info("Webhook delivered: %s → %s", event_type, url)
            return True
        except Exception as exc:
            logger.error("Webhook failed after retries: %s — %s", url, exc)
            return False

    @staticmethod
    def verify_signature(payload_body: str, signature_header: str, secret: str) -> bool:
        """
        Verify an incoming webhook signature from Arc platform.

        signature_header format: "t={timestamp},v1={hex}"
        """
        try:
            parts = dict(p.split("=", 1) for p in signature_header.split(","))
            ts = parts["t"]
            provided_sig = parts["v1"]
            signed = f"{ts}.{payload_body}"
            expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, provided_sig)
        except Exception:
            return False

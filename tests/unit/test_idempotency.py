"""Unit tests for IdempotencyStore with mocked Redis."""

from unittest.mock import MagicMock

from src.infrastructure.cache.redis_client import IdempotencyStore


class TestIdempotencyStore:
    def _store(self):
        redis = MagicMock()
        redis.get.return_value = None
        redis.exists.return_value = 0
        redis.set.return_value = True
        return IdempotencyStore(client=redis), redis

    def test_get_returns_none_when_missing(self):
        store, _ = self._store()
        assert store.get("nonexistent") is None

    def test_set_and_get(self):
        store, redis = self._store()
        redis.get.return_value = '{"status": "paid", "invoice_id": "123"}'
        result = store.get("key-1")
        assert result["status"] == "paid"

    def test_exists_false(self):
        store, _ = self._store()
        assert not store.exists("key-x")

    def test_lock_acquired(self):
        store, redis = self._store()
        redis.set.return_value = True
        assert store.lock("payment-lock")

    def test_lock_not_acquired_when_taken(self):
        store, redis = self._store()
        redis.set.return_value = False
        assert not store.lock("already-locked")

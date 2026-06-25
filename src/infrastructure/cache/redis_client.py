"""Redis client for idempotency and caching."""

import json
import logging
from functools import lru_cache

import redis

from src.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


class IdempotencyStore:
    """
    Redis-backed idempotency store.

    Prevents duplicate payment processing when clients retry requests.
    Keys expire after settings.idempotency_ttl seconds (default 24h).
    """

    PREFIX = "idempotency:"

    def __init__(self, client: redis.Redis | None = None) -> None:
        self._r = client or get_redis()

    def get(self, key: str) -> dict | None:
        raw = self._r.get(f"{self.PREFIX}{key}")
        if raw:
            return json.loads(raw)
        return None

    def set(self, key: str, result: dict) -> None:
        self._r.setex(
            f"{self.PREFIX}{key}",
            settings.idempotency_ttl,
            json.dumps(result, default=str),
        )

    def exists(self, key: str) -> bool:
        return bool(self._r.exists(f"{self.PREFIX}{key}"))

    def lock(self, key: str, ttl: int = 30) -> bool:
        """Acquire a distributed lock (NX). Returns True if acquired."""
        return bool(self._r.set(f"lock:{key}", "1", nx=True, ex=ttl))

    def unlock(self, key: str) -> None:
        self._r.delete(f"lock:{key}")

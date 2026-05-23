"""Async token-bucket rate limiter for provider calls."""

from __future__ import annotations

import asyncio
import logging
import time


class AsyncTokenBucketRateLimiter:
    """Bound request starts to a configurable token bucket."""

    def __init__(
        self,
        *,
        capacity: int,
        refill_rate_per_second: float,
        logger: logging.Logger | None = None,
    ) -> None:
        if capacity < 1:
            raise ValueError("rate limit capacity must be >= 1")
        if refill_rate_per_second <= 0:
            raise ValueError("rate limit refill rate must be > 0")
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._refill_rate = refill_rate_per_second
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()
        self._logger = logger or logging.getLogger(__name__)

    @property
    def capacity(self) -> int:
        return int(self._capacity)

    @property
    def refill_rate_per_second(self) -> float:
        return self._refill_rate

    async def acquire(self, *, label: str) -> None:
        """Wait until one token is available."""

        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    self._logger.debug(
                        "rate limiter acquired token label=%s remaining=%.2f capacity=%s refill_rate=%.3f",
                        label,
                        self._tokens,
                        self.capacity,
                        self._refill_rate,
                    )
                    return
                wait_seconds = (1 - self._tokens) / self._refill_rate
                self._logger.info(
                    "rate limiter waiting %.3fs label=%s capacity=%s refill_rate=%.3f",
                    wait_seconds,
                    label,
                    self.capacity,
                    self._refill_rate,
                )
            await asyncio.sleep(wait_seconds)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._updated_at
        self._updated_at = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)

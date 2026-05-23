from __future__ import annotations

import pytest

from src.services.rate_limiter import AsyncTokenBucketRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_acquires_available_tokens():
    limiter = AsyncTokenBucketRateLimiter(capacity=2, refill_rate_per_second=1000)

    await limiter.acquire(label="first")
    await limiter.acquire(label="second")

    assert limiter.capacity == 2
    assert limiter.refill_rate_per_second == 1000


def test_rate_limiter_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        AsyncTokenBucketRateLimiter(capacity=0, refill_rate_per_second=1)

    with pytest.raises(ValueError):
        AsyncTokenBucketRateLimiter(capacity=1, refill_rate_per_second=0)

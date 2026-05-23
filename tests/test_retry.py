from __future__ import annotations

import logging

import pytest

from ai.providers.base import ProviderError
from src.services.retry import RetryExhausted, retry_async


@pytest.mark.asyncio
async def test_retry_async_success():
    call_count = 0

    async def transient_fail():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ProviderError("transient error")
        return "success"

    res = await retry_async(
        transient_fail,
        attempts=3,
        base_delay_seconds=0.01,
        timeout_seconds=1.0,
        logger=logging.getLogger("test"),
        action="test_action",
    )

    assert res == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_async_exhausted():
    async def always_fail():
        raise ProviderError("permanent error")

    with pytest.raises(RetryExhausted):
        await retry_async(
            always_fail,
            attempts=2,
            base_delay_seconds=0.01,
            timeout_seconds=1.0,
            logger=logging.getLogger("test"),
            action="test_action",
        )

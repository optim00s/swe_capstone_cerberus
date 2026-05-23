"""Small retry helper with exponential backoff and asyncio timeouts."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from ai.providers.base import ProviderError

T = TypeVar("T")


class RetryExhausted(ProviderError):
    """Raised when the retry budget is exhausted."""


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    base_delay_seconds: float,
    timeout_seconds: float,
    logger: logging.Logger,
    action: str,
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await asyncio.wait_for(operation(), timeout=timeout_seconds)
        except (ProviderError, OSError, TimeoutError, asyncio.TimeoutError) as exc:
            last_error = exc
            if attempt >= attempts:
                break
            delay = base_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "%s failed on attempt %s/%s: %s: %s",
                action,
                attempt,
                attempts,
                type(exc).__name__,
                str(exc) or "<no message>",
            )
            await asyncio.sleep(delay)
    error_type = type(last_error).__name__ if last_error is not None else "unknown"
    error_text = str(last_error) if last_error is not None else "no error captured"
    raise RetryExhausted(
        f"{action} failed after {attempts} attempts: {error_type}: {error_text or '<no message>'}"
    ) from last_error

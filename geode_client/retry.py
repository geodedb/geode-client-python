"""Retry policy and async retry helper (mirrors Go retry.go).

Defaults: 3 attempts, 1s initial backoff, 30s max backoff, 2.0x multiplier.
Only retryable Geode errors (serialization/deadlock, transport, timeout) are
retried, as classified by :func:`geode_client.client.is_retryable_error`.
"""

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from .client import is_retryable_error

T = TypeVar("T")

_DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_INITIAL_BACKOFF = 1.0  # seconds
_DEFAULT_MAX_BACKOFF = 30.0  # seconds
_DEFAULT_MULTIPLIER = 2.0


@dataclass
class RetryPolicy:
    """Configures retry behavior for transient (retryable) errors."""

    max_attempts: int = _DEFAULT_MAX_ATTEMPTS
    initial_backoff: float = _DEFAULT_INITIAL_BACKOFF
    max_backoff: float = _DEFAULT_MAX_BACKOFF
    multiplier: float = _DEFAULT_MULTIPLIER

    def backoff(self, attempt: int) -> float:
        """Backoff (seconds) for ``attempt`` (1-indexed), clamped to max."""
        if attempt < 1:
            attempt = 1
        delay = self.initial_backoff * (self.multiplier ** (attempt - 1))
        return self.max_backoff if delay > self.max_backoff else delay


def default_retry_policy() -> RetryPolicy:
    """Return a RetryPolicy with the reference defaults."""
    return RetryPolicy()


async def retry(fn: Callable[[], Awaitable[T]], policy: RetryPolicy) -> T:
    """Call ``fn`` up to ``policy.max_attempts`` times, retrying retryable errors.

    Non-retryable errors are raised immediately. Between retries, sleeps for
    ``policy.backoff(attempt)`` seconds.
    """
    max_attempts = policy.max_attempts if policy.max_attempts >= 1 else 1
    last_exc: BaseException
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except BaseException as exc:  # noqa: BLE001 - re-raised below
            last_exc = exc
            if not is_retryable_error(exc):
                raise
            if attempt == max_attempts:
                break
            await asyncio.sleep(policy.backoff(attempt))
    raise last_exc

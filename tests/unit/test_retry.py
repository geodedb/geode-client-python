"""Unit tests for RetryPolicy and retry.

Retry classification uses the authoritative ``geode_client.client``
predicates, which key off the ISO/IEC 39075 SQLSTATE ``code`` carried by
``QueryError`` (serialization 40001 / deadlock 40P01,40502 are retryable).
"""

import pytest

from geode_client import QueryError, RetryPolicy, default_retry_policy, retry


class TestRetryPolicy:
    def test_defaults(self):
        p = default_retry_policy()
        assert p.max_attempts == 3
        assert p.initial_backoff == 1.0
        assert p.max_backoff == 30.0
        assert p.multiplier == 2.0

    def test_backoff_exponential(self):
        p = default_retry_policy()
        assert p.backoff(1) == 1.0
        assert p.backoff(2) == 2.0
        assert p.backoff(3) == 4.0

    def test_backoff_clamped(self):
        p = RetryPolicy(
            max_attempts=10, initial_backoff=1.0, max_backoff=5.0, multiplier=2.0
        )
        assert p.backoff(10) == 5.0

    def test_backoff_min_attempt(self):
        p = default_retry_policy()
        assert p.backoff(0) == 1.0


@pytest.fixture
def no_sleep(monkeypatch):
    import importlib

    async def fake_sleep(_):
        return None

    retry_mod = importlib.import_module("geode_client.retry")
    monkeypatch.setattr(retry_mod.asyncio, "sleep", fake_sleep)


class TestRetry:
    @pytest.mark.asyncio
    async def test_success_first_try(self):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            return "ok"

        result = await retry(fn, default_retry_policy())
        assert result == "ok"
        assert calls["n"] == 1

    @pytest.mark.asyncio
    async def test_non_retryable_returns_immediately(self):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            raise QueryError("syntax", code="42000")

        with pytest.raises(QueryError):
            await retry(fn, default_retry_policy())
        assert calls["n"] == 1

    @pytest.mark.asyncio
    async def test_retries_retryable_then_succeeds(self, no_sleep):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise QueryError("serialization", code="40001")
            return "ok"

        result = await retry(fn, default_retry_policy())
        assert result == "ok"
        assert calls["n"] == 3

    @pytest.mark.asyncio
    async def test_exhausts_attempts(self, no_sleep):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            raise QueryError("ser", code="40001")

        with pytest.raises(QueryError):
            await retry(fn, default_retry_policy())
        assert calls["n"] == 3  # max_attempts

"""Unit tests for RetryPolicy and retry."""

import pytest

from geode_client import DriverError, RetryPolicy, default_retry_policy, retry


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
            raise DriverError(code="x", status_class="42000", message="syntax")

        with pytest.raises(DriverError):
            await retry(fn, default_retry_policy())
        assert calls["n"] == 1

    @pytest.mark.asyncio
    async def test_retries_retryable_then_succeeds(self, no_sleep):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise DriverError(
                    code="x", status_class="40001", message="serialization"
                )
            return "ok"

        result = await retry(fn, default_retry_policy())
        assert result == "ok"
        assert calls["n"] == 3

    @pytest.mark.asyncio
    async def test_exhausts_attempts(self, no_sleep):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            raise DriverError(code="x", status_class="40001", message="ser")

        with pytest.raises(DriverError):
            await retry(fn, default_retry_policy())
        assert calls["n"] == 3  # max_attempts

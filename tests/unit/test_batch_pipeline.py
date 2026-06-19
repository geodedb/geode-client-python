"""Unit tests for Connection.batch_exec and pipeline_exec using a fake transport."""

import asyncio

import pytest

from geode_client import Statement
from geode_client.client import Connection
from geode_client.errors import DriverError


def _make_connection(execute_side_effect=None):
    conn = Connection(host="h", port=1)
    conn._connected = True

    class FakeTransport:
        session_id = "s1"

        def __init__(self):
            self.begun = 0
            self.committed = 0
            self.rolled_back = 0
            self.executed = []

        async def begin(self, req):
            self.begun += 1

        async def commit(self, req):
            self.committed += 1

        async def rollback(self, req):
            self.rolled_back += 1

    transport = FakeTransport()
    conn._transport = transport

    async def fake_execute(text, params=None):
        transport.executed.append(text)
        if execute_side_effect is not None:
            execute_side_effect(text)

    conn.execute = fake_execute  # type: ignore[method-assign]

    async def fake_begin():
        await transport.begin(None)

    async def fake_commit():
        await transport.commit(None)

    async def fake_rollback():
        await transport.rollback(None)

    conn.begin = fake_begin  # type: ignore[method-assign]
    conn.commit = fake_commit  # type: ignore[method-assign]
    conn.rollback = fake_rollback  # type: ignore[method-assign]
    return conn, transport


class TestBatchExec:
    @pytest.mark.asyncio
    async def test_empty_is_noop(self):
        conn, t = _make_connection()
        await conn.batch_exec([])
        assert t.begun == 0
        assert t.committed == 0

    @pytest.mark.asyncio
    async def test_single_transaction_commit(self):
        conn, t = _make_connection()
        await conn.batch_exec([Statement("CREATE (a)"), Statement("CREATE (b)")])
        assert t.begun == 1
        assert t.committed == 1
        assert t.executed == ["CREATE (a)", "CREATE (b)"]

    @pytest.mark.asyncio
    async def test_rollback_on_nonretryable_error(self):
        def boom(text):
            if text == "CREATE (b)":
                raise DriverError(code="US001", status_class="42000", message="syntax")

        conn, t = _make_connection(execute_side_effect=boom)
        with pytest.raises(DriverError):
            await conn.batch_exec([Statement("CREATE (a)"), Statement("CREATE (b)")])
        assert t.rolled_back >= 1
        assert t.committed == 0

    @pytest.mark.asyncio
    async def test_retries_retryable_error(self):
        calls = {"n": 0}

        def flaky(text):
            calls["n"] += 1
            # Fail the first whole-batch attempt on the first statement,
            # succeed thereafter.
            if calls["n"] == 1:
                raise DriverError(
                    code="SER", status_class="40001", message="serialization"
                )

        conn, t = _make_connection(execute_side_effect=flaky)
        # Speed up: patch retry backoff to no-op sleep.

        async def no_sleep(_):
            return None

        orig = asyncio.sleep
        asyncio.sleep = no_sleep  # type: ignore[assignment]
        try:
            await conn.batch_exec([Statement("CREATE (a)")])
        finally:
            asyncio.sleep = orig  # type: ignore[assignment]
        assert t.committed == 1


class TestPipelineExec:
    @pytest.mark.asyncio
    async def test_empty_is_noop(self):
        conn, t = _make_connection()
        await conn.pipeline_exec([])
        assert t.begun == 0

    @pytest.mark.asyncio
    async def test_chunking(self):
        conn, t = _make_connection()
        stmts = [Statement(f"CREATE (n{i})") for i in range(250)]
        await conn.pipeline_exec(stmts, chunk_size=100, max_workers=8)
        # 250 statements / 100 per chunk = 3 chunks => 3 transactions.
        assert t.begun == 3
        assert t.committed == 3
        assert len(t.executed) == 250

    @pytest.mark.asyncio
    async def test_concurrency_bound(self):
        # Track concurrent in-flight chunk count via a shared counter.
        state = {"cur": 0, "max": 0}
        gate = asyncio.Event()

        conn = Connection(host="h", port=1)
        conn._connected = True

        async def fake_batch_exec(statements):
            state["cur"] += 1
            state["max"] = max(state["max"], state["cur"])
            await asyncio.sleep(0)
            await gate.wait()
            state["cur"] -= 1

        conn.batch_exec = fake_batch_exec  # type: ignore[method-assign]
        stmts = [Statement(f"q{i}") for i in range(100)]  # 1 per chunk
        task = asyncio.create_task(
            conn.pipeline_exec(stmts, chunk_size=1, max_workers=4)
        )
        await asyncio.sleep(0.05)
        assert state["max"] <= 4
        gate.set()
        await task

    @pytest.mark.asyncio
    async def test_first_error_stops_new_launches(self):
        launched = {"n": 0}

        conn = Connection(host="h", port=1)
        conn._connected = True

        async def fake_batch_exec(statements):
            launched["n"] += 1
            await asyncio.sleep(0)
            raise DriverError(code="X", status_class="42000", message="boom")

        conn.batch_exec = fake_batch_exec  # type: ignore[method-assign]
        stmts = [Statement(f"q{i}") for i in range(100)]
        with pytest.raises(DriverError):
            await conn.pipeline_exec(stmts, chunk_size=1, max_workers=2)
        # First error stops launching new chunks: far fewer than 100 launched.
        assert launched["n"] < 100

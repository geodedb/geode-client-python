# Geode Python Driver Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `geode-client-python` to feature parity with the reference `geode-client-go` driver by porting twelve missing capabilities with faithful semantics.

**Architecture:** Add new focused modules (`crypto.py`, `quote.py`, `schema.py`, `retry.py`, `batch.py`) and a typed-graph/errors layer, plus extend existing `transport.py` (DSN tenant/role + redact + format_dsn), `client.py` (HELLO tenant/role + Statement/batch_exec/pipeline_exec + query_row), `types.py` (Node/Edge/Path + converters), `pool.py` (DSN factory), and `errors`/exception hierarchy. Every public symbol is re-exported from `geode_client/__init__.py`. All async API style, dataclasses, ruff/mypy clean.

**Tech Stack:** Python 3.9+, asyncio, `cryptography` (AES-GCM + HKDF + HMAC), protobuf, pytest + pytest-asyncio, Hypothesis, pytest-benchmark, ruff, mypy.

## Global Constraints

- Python 3.9+ compatible. mypy.ini pins `python_version` to 3.9 (warns under newer mypy but passes); use `from __future__ import annotations`-free style consistent with existing modules (they use `typing.Optional`, `typing.List`, etc. and also bare `list[...]` in `transport.py`). Match the file you edit.
- Match the existing exception hierarchy: all client errors subclass `GeodeError` (in `geode_client/client.py`). New error types subclass `GeodeError`.
- Validation helpers live in `geode_client/validate.py` and raise `ValidationError` (a `ValueError` subclass). Quoting helpers (this plan) raise new errors that subclass `GeodeError` to mirror Go's `ErrInvalidIdent`/`ErrInvalidString`.
- ruff config: `ruff.toml`. Run `make lint` (checks `geode_client/` only) and `make fmt-check`. Tests are NOT linted by `make lint` but keep them clean.
- mypy runs on `geode_client/` only (`make typecheck`), with `--ignore-missing-imports`. Type-annotate all new public functions.
- Commit after each task with a Conventional Commits message (commitizen `check` runs in pre-commit). End every commit body with:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Tests: unit in `tests/unit/`, property in `tests/property/test_hypothesis.py`, integration in `tests/integration/` (marked `integration`, must import/collect without a server), benchmarks in `benchmarks/` using the `benchmark` fixture.
- Do NOT touch the default branch. All work is on branch `feat/driver-parity-2026-06`.
- Exact Go semantic constants to honor verbatim:
  - Crypto: AES-256-GCM, key size 32, nonce size 12 (prepended), HKDF-SHA256 salt=`None`, info `b"geode-encrypt"` (enc key) and `b"geode-hmac"` (hmac key), std base64, HMAC-SHA256 lowercase hex.
  - Retry: max_attempts=3, initial_backoff=1.0s, max_backoff=30.0s, multiplier=2.0; backoff(attempt)=initial*multiplier**(attempt-1) clamped to max; retry only retryable errors.
  - Status classes: auth `"28000"` + `"08P01"`; syntax `"42000"`; retryable `"40001"` (serialization) + `"40502"` (deadlock).
  - Pipeline: default chunk_size=100, default max_workers=8; first-error stops launching new chunks, in-flight complete; each chunk via batch_exec (single tx + retry).
  - Redact token: `"***"`; credential params (case-insensitive): `user`, `username`, `pass`, `password`.
  - Quote ident: allow `[A-Za-z_]`, digits anywhere (incl first), hyphen anywhere except first; empty or other chars -> error.
  - Quote string: reject chars `< 0x20` or `== 0x7F`; escape `\` -> `\\` first, then `'` -> `''`; wrap in single quotes.
  - Schema parse: keep lines whose uppercased trim starts with `CREATE`/`MERGE`/`MATCH`/`DELETE`; drop blank, `//`, `--`; split each kept line on `;`.

---

## File Structure

- Create `geode_client/errors.py` — status-class constants, `DriverError(GeodeError)`, classifiers `is_auth_error`, `is_syntax_error`, `is_retryable_error`, `NoRowsError(GeodeError)`. (Task 8 + 12; foundation for retry/batch.)
- Create `geode_client/retry.py` — `RetryPolicy` dataclass, `default_retry_policy()`, async `retry(coro_fn, policy)`. (Task 11.)
- Create `geode_client/crypto.py` — `Cipher`, `CryptoError(GeodeError)`. (Task 4.)
- Create `geode_client/quote.py` — `quote_ident`, `quote_string`, `sanitize_graph_name`, `InvalidIdentifierError`, `InvalidStringError`. (Task 6.)
- Create `geode_client/schema.py` — `Statement` re-export + `parse_schema_fs`. (Task 2; `Statement` defined in `batch.py`.)
- Create `geode_client/batch.py` — `Statement` dataclass, module constants `DEFAULT_CHUNK_SIZE`, `DEFAULT_MAX_WORKERS`, helper `chunk_statements`. (Task 3.)
- Modify `geode_client/transport.py` — DSN `tenant`/`tenant_id`/`role` params on `TransportConfig`; `redact_dsn`; `format_dsn`. (Tasks 1, 5, 10.)
- Modify `geode_client/client.py` — `Connection` accepts `tenant`/`role`, sends them in HELLO; `batch_exec`, `pipeline_exec`, `query_row`. (Tasks 1, 3, 8.)
- Modify `geode_client/types.py` — `Node`, `Edge`, `Path` dataclasses + `as_node`, `as_edge`, `as_path`. (Task 9.)
- Modify `geode_client/pool.py` — `create_pool_from_dsn` factory. (Task 7.)
- Modify `geode_client/__init__.py` — re-export all new public symbols. (Every task.)
- Tests: one new file per feature under `tests/unit/`; extend `tests/property/test_hypothesis.py`; add `tests/integration/test_parity.py`; add `benchmarks/bench_crypto.py`.

---

## Task 1: HELLO tenant_id + role config and DSN params

**Files:**

- Modify: `geode_client/transport.py` (TransportConfig fields + parse_dsn param map)
- Modify: `geode_client/client.py` (Connection **init** + connect HELLO)
- Test: `tests/unit/test_hello_tenant_role.py`

**Interfaces:**

- Produces: `TransportConfig.tenant: str = ""`, `TransportConfig.role: str = ""`; `Connection(..., tenant: str = "", role: str = "")`; HELLO `HelloRequest` carries `tenant_id` and `role` when set.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_hello_tenant_role.py`:

```python
"""Unit tests for HELLO tenant_id and role config + DSN parsing."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from geode_client.client import Connection
from geode_client.transport import TransportConfig, TransportType, parse_dsn


class TestDSNTenantRole:
    def test_tenant_id_param(self):
        cfg = parse_dsn("quic://localhost:3141?tenant_id=acme")
        assert cfg.tenant == "acme"

    def test_tenant_alias(self):
        cfg = parse_dsn("quic://localhost:3141?tenant=acme")
        assert cfg.tenant == "acme"

    def test_role_param(self):
        cfg = parse_dsn("quic://localhost:3141?role=analyst")
        assert cfg.role == "analyst"

    def test_defaults_empty(self):
        cfg = parse_dsn("quic://localhost:3141")
        assert cfg.tenant == ""
        assert cfg.role == ""

    def test_config_defaults(self):
        cfg = TransportConfig(transport_type=TransportType.QUIC, host="h", port=1)
        assert cfg.tenant == ""
        assert cfg.role == ""


class TestConnectionHello:
    def test_connection_accepts_tenant_role(self):
        conn = Connection(host="h", port=1, tenant="acme", role="analyst")
        assert conn.tenant == "acme"
        assert conn.role == "analyst"

    @pytest.mark.asyncio
    async def test_hello_request_includes_tenant_and_role(self, monkeypatch):
        conn = Connection(host="h", port=1, tenant="acme", role="analyst")

        captured = {}

        class FakeTransport:
            session_id = "s1"

            async def connect(self):
                return None

            async def hello(self, req):
                captured["req"] = req
                resp = MagicMock()
                resp.success = True
                resp.error_message = ""
                return resp

            async def close(self):
                return None

        monkeypatch.setattr(
            "geode_client.client.create_transport",
            lambda config: FakeTransport(),
        )
        await conn.connect()
        req = captured["req"]
        assert req.tenant_id == "acme"
        assert req.role == "analyst"

    @pytest.mark.asyncio
    async def test_hello_request_omits_empty_tenant_role(self, monkeypatch):
        conn = Connection(host="h", port=1)
        captured = {}

        class FakeTransport:
            session_id = "s1"

            async def connect(self):
                return None

            async def hello(self, req):
                captured["req"] = req
                resp = MagicMock()
                resp.success = True
                resp.error_message = ""
                return resp

            async def close(self):
                return None

        monkeypatch.setattr(
            "geode_client.client.create_transport",
            lambda config: FakeTransport(),
        )
        await conn.connect()
        req = captured["req"]
        assert req.HasField("tenant_id") is False
        assert req.HasField("role") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_hello_tenant_role.py -v`
Expected: FAIL — `TransportConfig` has no `tenant`/`role`; `Connection` has no `tenant`/`role`.

- [ ] **Step 3: Add fields to TransportConfig**

In `geode_client/transport.py`, in the `TransportConfig` dataclass, after `graph: str = ""` add:

```python
    tenant: str = ""  # Tenant identifier sent in HELLO (tenant_id)
    role: str = ""  # FLE role sent in HELLO for field-level access control
```

- [ ] **Step 4: Parse tenant/role in parse_dsn**

In `geode_client/transport.py`, inside `parse_dsn`, extend `_PARAM_MAP` (after the `("graph", ("graph",), str),` entry) with:

```python
            ("tenant", ("tenant", "tenant_id"), str),
            ("role", ("role",), str),
```

- [ ] **Step 5: Add tenant/role to Connection**

In `geode_client/client.py`, in `Connection.__init__` signature, after `graph: str = "",` add:

```python
        tenant: str = "",
        role: str = "",
```

After `self.graph = graph` add:

```python
        self.tenant = tenant
        self.role = role
```

In `connect()`, where `TransportConfig(...)` is built, add `tenant=self.tenant,` and `role=self.role,` after `graph=self.graph,`.

Then change the `HelloRequest(...)` construction to include tenant_id and role only when set:

```python
        hello_req = HelloRequest(
            username=self.username,
            password=self.password,
            client_name=self.hello_name,
            client_version=self.hello_ver,
            wanted_conformance=self.conformance,
            graph=self.graph if self.graph else None,
            tenant_id=self.tenant if self.tenant else None,
            role=self.role if self.role else None,
        )
```

- [ ] **Step 6: Propagate tenant/role through Client.from_url**

In `geode_client/client.py`, in `Client.from_url`, add to the `cls(...)` call after `graph=config.graph,`:

```python
            tenant=config.tenant,
            role=config.role,
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_hello_tenant_role.py -v`
Expected: PASS (7 tests).

- [ ] **Step 8: Lint, typecheck, full unit run**

Run: `make lint && make typecheck && .venv/bin/pytest tests/unit/ -q`
Expected: clean; all unit tests pass.

- [ ] **Step 9: Commit**

```bash
git add geode_client/transport.py geode_client/client.py tests/unit/test_hello_tenant_role.py
git commit -m "feat: expose tenant_id and role in config, DSN, and HELLO"
```

---

## Task 2: ParseSchemaFS (parse_schema_fs)

**Files:**

- Create: `geode_client/batch.py` (defines `Statement` — needed first; full batch logic in Task 3)
- Create: `geode_client/schema.py`
- Modify: `geode_client/__init__.py`
- Test: `tests/unit/test_schema.py`

**Interfaces:**

- Produces: `Statement` dataclass `{query: str, params: Optional[Dict[str, Any]] = None}`; `parse_schema_fs(path: Union[str, os.PathLike]) -> List[Statement]`.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_schema.py`:

```python
"""Unit tests for parse_schema_fs."""

import pytest

from geode_client import Statement, parse_schema_fs


@pytest.fixture
def schema_dir(tmp_path):
    (tmp_path / "01_nodes.gql").write_text(
        "// comment line\n"
        "-- sql style comment\n"
        "\n"
        "CREATE (n:Person {name: 'Alice'});\n"
        "MERGE (m:Company {name: 'Acme'});\n"
        "SELECT 1;\n"  # non-GQL keyword, dropped
    )
    (tmp_path / "02_edges.gql").write_text(
        "MATCH (a), (b) CREATE (a)-[:KNOWS]->(b);\n"
        "DELETE (x);\n"
    )
    (tmp_path / "notes.txt").write_text("CREATE (ignored);")  # non-.gql
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "03_more.gql").write_text("CREATE (ignored);")  # subdir not traversed
    return tmp_path


class TestParseSchemaFS:
    def test_returns_statements(self, schema_dir):
        stmts = parse_schema_fs(schema_dir)
        queries = [s.query for s in stmts]
        assert "CREATE (n:Person {name: 'Alice'})" in queries
        assert "MERGE (m:Company {name: 'Acme'})" in queries
        assert "MATCH (a), (b) CREATE (a)-[:KNOWS]->(b)" in queries
        assert "DELETE (x)" in queries

    def test_filters_comments_and_blanks(self, schema_dir):
        stmts = parse_schema_fs(schema_dir)
        for s in stmts:
            assert s.query.strip() != ""
            assert not s.query.startswith("//")
            assert not s.query.startswith("--")

    def test_drops_non_gql_keywords(self, schema_dir):
        stmts = parse_schema_fs(schema_dir)
        assert all(not s.query.upper().startswith("SELECT") for s in stmts)

    def test_ignores_non_gql_files(self, schema_dir):
        stmts = parse_schema_fs(schema_dir)
        assert all("ignored" not in s.query for s in stmts)

    def test_does_not_traverse_subdirs(self, schema_dir):
        stmts = parse_schema_fs(schema_dir)
        assert all("ignored" not in s.query for s in stmts)

    def test_semicolon_split_multiple_per_line(self, tmp_path):
        (tmp_path / "x.gql").write_text("CREATE (a); CREATE (b);")
        stmts = parse_schema_fs(tmp_path)
        assert [s.query for s in stmts] == ["CREATE (a)", "CREATE (b)"]

    def test_missing_dir_raises(self, tmp_path):
        with pytest.raises(OSError):
            parse_schema_fs(tmp_path / "nope")

    def test_statement_no_params_default(self):
        s = Statement(query="MATCH (n) RETURN n")
        assert s.query == "MATCH (n) RETURN n"
        assert s.params is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_schema.py -v`
Expected: FAIL — cannot import `Statement`/`parse_schema_fs`.

- [ ] **Step 3: Create batch.py with Statement**

Create `geode_client/batch.py`:

```python
"""Batch and pipeline execution support for Geode.

Mirrors the Go reference (batch.go): a Statement pairs a GQL query with
optional bound parameters; BatchExec runs statements in a single
transaction with retry; PipelineExec runs chunks concurrently.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Default number of statements per chunk in pipeline_exec (Go: DefaultChunkSize).
DEFAULT_CHUNK_SIZE = 100

# Default maximum number of concurrent chunk workers (Go: DefaultMaxWorkers).
DEFAULT_MAX_WORKERS = 8


@dataclass
class Statement:
    """A GQL query paired with its optional bound parameters."""

    query: str
    params: Optional[Dict[str, Any]] = None


def chunk_statements(
    statements: List[Statement], chunk_size: int
) -> List[List[Statement]]:
    """Split statements into contiguous chunks of at most chunk_size."""
    if chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE
    return [
        statements[i : i + chunk_size]
        for i in range(0, len(statements), chunk_size)
    ]
```

- [ ] **Step 4: Create schema.py**

Create `geode_client/schema.py`:

```python
"""Schema file parsing for Geode (mirrors Go schema.go ParseSchemaFS).

Reads ``*.gql`` files from a directory, strips blank lines, line comments
(``//`` and ``--``), and lines that do not begin with a recognised GQL
keyword (CREATE, MERGE, MATCH, DELETE), then splits the surviving lines on
``;`` into individual statements.
"""

import os
from typing import List, Union

from .batch import Statement

_GQL_PREFIXES = ("CREATE", "MERGE", "MATCH", "DELETE")


def parse_schema_fs(path: Union[str, "os.PathLike[str]"]) -> List[Statement]:
    """Read all ``.gql`` files directly under ``path`` and return Statements.

    Subdirectories are not traversed; only direct children matching
    ``*.gql`` are read. Raises OSError if the directory cannot be read.
    """
    statements: List[Statement] = []
    entries = sorted(os.listdir(path))
    for name in entries:
        full = os.path.join(path, name)
        if os.path.isdir(full) or not name.endswith(".gql"):
            continue
        with open(full, encoding="utf-8") as handle:
            content = handle.read()
        for line in content.split("\n"):
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("//") or trimmed.startswith("--"):
                continue
            upper = trimmed.upper()
            if not upper.startswith(_GQL_PREFIXES):
                continue
            for part in trimmed.split(";"):
                part = part.strip()
                if part:
                    statements.append(Statement(query=part))
    return statements
```

- [ ] **Step 5: Export from **init**.py**

In `geode_client/__init__.py`, add an import block (after the existing `from .auth import ...` block):

```python
from .batch import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_MAX_WORKERS,
    Statement,
)
from .schema import parse_schema_fs
```

Add to `__all__` (insert near the query-building section):

```python
    # Batch / schema
    "Statement",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_MAX_WORKERS",
    "parse_schema_fs",
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_schema.py -v`
Expected: PASS (8 tests).

- [ ] **Step 7: Lint, typecheck**

Run: `make lint && make typecheck`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add geode_client/batch.py geode_client/schema.py geode_client/__init__.py tests/unit/test_schema.py
git commit -m "feat: add Statement dataclass and parse_schema_fs"
```

---

## Task 3: batch_exec + pipeline_exec on Connection

**Files:**

- Modify: `geode_client/client.py` (add `batch_exec`, `pipeline_exec` to `Connection`)
- Modify: `geode_client/__init__.py` (no new symbols; `Statement` already exported)
- Test: `tests/unit/test_batch_pipeline.py`

**Interfaces:**

- Consumes: `Statement` (Task 2), `default_retry_policy`/`retry` (Task 11 — implemented before this in execution order; if executing strictly in plan order, Task 11 must precede Task 3, see Execution Order note). `chunk_statements`, `DEFAULT_CHUNK_SIZE`, `DEFAULT_MAX_WORKERS` (Task 2).
- Produces: `Connection.batch_exec(self, statements: List[Statement]) -> None` (runs all in a single transaction with retry); `Connection.pipeline_exec(self, statements: List[Statement], chunk_size: int = 0, max_workers: int = 0) -> None` (concurrent chunks, first-error stops new launches).

> **Execution Order note:** `batch_exec` retries via `default_retry_policy()`/`retry` from Task 11. Implement Task 11 before Task 3 (or inline-import inside the method to avoid a hard ordering dependency). This plan imports `retry`/`default_retry_policy` at module top of `client.py`; ensure Task 11 is merged first.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_batch_pipeline.py`:

```python
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
        import geode_client.retry as retry_mod

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_batch_pipeline.py -v`
Expected: FAIL — `Connection` has no `batch_exec`/`pipeline_exec`; `DriverError` not importable (depends on Task 8).

> If Task 8 not yet merged, this task depends on it. Implement Tasks 8 and 11 before Task 3.

- [ ] **Step 3: Add imports to client.py**

In `geode_client/client.py`, add near the existing imports:

```python
from .batch import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_MAX_WORKERS,
    Statement,
    chunk_statements,
)
from .errors import is_retryable_error
from .retry import default_retry_policy, retry
```

- [ ] **Step 4: Implement batch_exec on Connection**

In `geode_client/client.py`, add these methods to `Connection` (after `batch`):

```python
    async def _batch_exec_tx(self, statements: List[Statement]) -> None:
        """Run all statements inside a single transaction (no retry)."""
        await self.begin()
        try:
            for i, stmt in enumerate(statements):
                try:
                    await self.execute(stmt.query, stmt.params)
                except (QueryError, GeodeError) as exc:
                    raise GeodeError(f"statement {i + 1}: {exc}") from exc
        except BaseException:
            try:
                await self.rollback()
            except Exception:
                pass
            raise
        await self.commit()

    async def batch_exec(self, statements: List[Statement]) -> None:
        """Execute statements in a single transaction with automatic retry.

        Mirrors Go Pool.BatchExec: a single transaction pins the connection
        for the whole batch; retryable errors (serialization/deadlock) are
        retried per the default retry policy. An empty list is a no-op.
        """
        if not statements:
            return

        async def attempt() -> None:
            await self._batch_exec_tx(statements)

        await retry(attempt, default_retry_policy())

    async def pipeline_exec(
        self,
        statements: List[Statement],
        chunk_size: int = 0,
        max_workers: int = 0,
    ) -> None:
        """Execute statements in concurrent chunks via batch_exec.

        Splits ``statements`` into chunks of ``chunk_size`` (default 100) and
        runs up to ``max_workers`` (default 8) chunks concurrently. The first
        error stops launching new chunks; in-flight chunks complete. The first
        error encountered is raised.
        """
        if not statements:
            return
        if chunk_size <= 0:
            chunk_size = DEFAULT_CHUNK_SIZE
        if max_workers <= 0:
            max_workers = DEFAULT_MAX_WORKERS

        chunks = chunk_statements(statements, chunk_size)
        sem = asyncio.Semaphore(max_workers)
        first_error: List[BaseException] = []
        tasks: List[asyncio.Task] = []

        async def run_chunk(chunk: List[Statement]) -> None:
            async with sem:
                try:
                    await self.batch_exec(chunk)
                except BaseException as exc:  # noqa: BLE001 - record first error
                    if not first_error:
                        first_error.append(exc)

        for chunk in chunks:
            if first_error:
                break
            tasks.append(asyncio.create_task(run_chunk(chunk)))

        if tasks:
            await asyncio.gather(*tasks)

        if first_error:
            raise first_error[0]
```

> Note: `is_retryable_error` import is required by Task 11's `retry`; the import line above keeps `client.py` self-consistent even though `retry` consumes it internally. If ruff flags `is_retryable_error` as unused, remove that single import line — `retry` imports it itself in `retry.py`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_batch_pipeline.py -v`
Expected: PASS (8 tests).

- [ ] **Step 6: Lint, typecheck, full unit run**

Run: `make lint && make typecheck && .venv/bin/pytest tests/unit/ -q`
Expected: clean; all pass. (If lint flags the unused `is_retryable_error` import in client.py, delete that line and re-run.)

- [ ] **Step 7: Commit**

```bash
git add geode_client/client.py tests/unit/test_batch_pipeline.py
git commit -m "feat: add Connection.batch_exec and pipeline_exec with retry semantics"
```

---

## Task 4: Crypto FLE module

**Files:**

- Create: `geode_client/crypto.py`
- Modify: `geode_client/__init__.py`
- Test: `tests/unit/test_crypto.py`
- Bench: `benchmarks/bench_crypto.py`

**Interfaces:**

- Produces: `CryptoError(GeodeError)`; `Cipher(master_key: bytes)` with `encrypt(bytes)->bytes`, `decrypt(bytes)->bytes`, `encrypt_string(str)->str`, `decrypt_string(str)->str`, `hmac_hex(str)->str`.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_crypto.py`:

```python
"""Unit tests for field-level encryption (crypto.py)."""

import base64

import pytest

from geode_client import Cipher, CryptoError

KEY = b"0123456789abcdef0123456789abcdef"  # exactly 32 bytes


class TestCipherConstruction:
    def test_short_key_rejected(self):
        with pytest.raises(CryptoError):
            Cipher(b"too-short")

    def test_min_length_key_ok(self):
        Cipher(KEY)

    def test_longer_key_ok(self):
        Cipher(KEY + b"extra-bytes")


class TestEncryptDecrypt:
    def test_round_trip_bytes(self):
        c = Cipher(KEY)
        pt = b"sensitive payload"
        ct = c.encrypt(pt)
        assert ct != pt
        assert c.decrypt(ct) == pt

    def test_nonce_prepended_makes_ciphertext_longer(self):
        c = Cipher(KEY)
        ct = c.encrypt(b"x")
        # 12-byte nonce + 1 byte data + 16-byte GCM tag = 29
        assert len(ct) == 12 + 1 + 16

    def test_encrypt_is_randomised(self):
        c = Cipher(KEY)
        assert c.encrypt(b"same") != c.encrypt(b"same")

    def test_round_trip_string(self):
        c = Cipher(KEY)
        enc = c.encrypt_string("hello world")
        # std base64 round-trips
        base64.b64decode(enc)
        assert c.decrypt_string(enc) == "hello world"

    def test_decrypt_too_short_raises(self):
        c = Cipher(KEY)
        with pytest.raises(CryptoError):
            c.decrypt(b"short")

    def test_decrypt_tampered_raises(self):
        c = Cipher(KEY)
        ct = bytearray(c.encrypt(b"hello"))
        ct[-1] ^= 0xFF
        with pytest.raises(CryptoError):
            c.decrypt(bytes(ct))

    def test_decrypt_string_bad_base64_raises(self):
        c = Cipher(KEY)
        with pytest.raises(CryptoError):
            c.decrypt_string("!!!not base64!!!")

    def test_cross_key_decrypt_fails(self):
        c1 = Cipher(KEY)
        c2 = Cipher(b"ffffffffffffffffffffffffffffffff")
        ct = c1.encrypt(b"secret")
        with pytest.raises(CryptoError):
            c2.decrypt(ct)


class TestHMAC:
    def test_hmac_deterministic(self):
        c = Cipher(KEY)
        assert c.hmac_hex("alice@example.com") == c.hmac_hex("alice@example.com")

    def test_hmac_hex_format(self):
        c = Cipher(KEY)
        digest = c.hmac_hex("x")
        assert len(digest) == 64
        assert digest == digest.lower()
        int(digest, 16)  # valid hex

    def test_hmac_differs_by_input(self):
        c = Cipher(KEY)
        assert c.hmac_hex("a") != c.hmac_hex("b")

    def test_hmac_differs_by_key(self):
        c1 = Cipher(KEY)
        c2 = Cipher(b"ffffffffffffffffffffffffffffffff")
        assert c1.hmac_hex("a") != c2.hmac_hex("a")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_crypto.py -v`
Expected: FAIL — cannot import `Cipher`/`CryptoError`.

- [ ] **Step 3: Implement crypto.py**

Create `geode_client/crypto.py`:

```python
"""Field-level encryption (FLE) for Geode (mirrors Go crypto/cipher.go).

Uses AES-256-GCM for authenticated encryption, HKDF-SHA256 to derive
separate encryption and HMAC keys from a master key (>= 32 bytes), and
HMAC-SHA256 for deterministic searchable hashing.
"""

import base64
import binascii
import hashlib
import hmac
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.hashes import SHA256

from .client import GeodeError

_KEY_SIZE = 32  # AES-256
_NONCE_SIZE = 12  # GCM nonce
_ENC_INFO = b"geode-encrypt"
_HMAC_INFO = b"geode-hmac"


class CryptoError(GeodeError):
    """Raised on encryption/decryption or key-derivation failure."""


def _derive_key(master_key: bytes, info: bytes) -> bytes:
    hkdf = HKDF(algorithm=SHA256(), length=_KEY_SIZE, salt=None, info=info)
    return hkdf.derive(master_key)


class Cipher:
    """Holds derived encryption and HMAC keys for field-level encryption."""

    def __init__(self, master_key: bytes) -> None:
        if len(master_key) < _KEY_SIZE:
            raise CryptoError(
                f"crypto: master key must be at least {_KEY_SIZE} bytes, "
                f"got {len(master_key)}"
            )
        self._enc_key = _derive_key(master_key, _ENC_INFO)
        self._hmac_key = _derive_key(master_key, _HMAC_INFO)
        self._aead = AESGCM(self._enc_key)

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt with AES-256-GCM; nonce is prepended to the ciphertext."""
        nonce = os.urandom(_NONCE_SIZE)
        ciphertext = self._aead.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt ciphertext produced by :meth:`encrypt`."""
        if len(ciphertext) < _NONCE_SIZE:
            raise CryptoError("crypto: ciphertext too short")
        nonce = ciphertext[:_NONCE_SIZE]
        data = ciphertext[_NONCE_SIZE:]
        try:
            return self._aead.decrypt(nonce, data, None)
        except InvalidTag as exc:
            raise CryptoError("crypto: decrypt: authentication failed") from exc

    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string and return standard base64-encoded ciphertext."""
        return base64.b64encode(self.encrypt(plaintext.encode("utf-8"))).decode(
            "ascii"
        )

    def decrypt_string(self, encoded: str) -> str:
        """Base64-decode then decrypt, returning the original string."""
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise CryptoError("crypto: base64 decode") from exc
        return self.decrypt(raw).decode("utf-8")

    def hmac_hex(self, data: str) -> str:
        """HMAC-SHA256 of data as a 64-char lowercase hex digest."""
        mac = hmac.new(self._hmac_key, data.encode("utf-8"), hashlib.sha256)
        return mac.hexdigest()
```

- [ ] **Step 4: Export from **init**.py**

In `geode_client/__init__.py`, add:

```python
from .crypto import Cipher, CryptoError
```

Add to `__all__`:

```python
    # Crypto (field-level encryption)
    "Cipher",
    "CryptoError",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_crypto.py -v`
Expected: PASS (16 tests).

- [ ] **Step 6: Add benchmarks**

Create `benchmarks/bench_crypto.py`:

```python
"""Benchmarks for field-level encryption (crypto.py)."""

from geode_client import Cipher

KEY = b"0123456789abcdef0123456789abcdef"
PAYLOAD = b"x" * 256
TEXT = "user@example.com"


class TestCryptoBenchmarks:
    def test_cipher_construction(self, benchmark):
        benchmark(Cipher, KEY)

    def test_encrypt(self, benchmark):
        cipher = Cipher(KEY)
        benchmark(cipher.encrypt, PAYLOAD)

    def test_decrypt(self, benchmark):
        cipher = Cipher(KEY)
        ct = cipher.encrypt(PAYLOAD)
        benchmark(cipher.decrypt, ct)

    def test_encrypt_string(self, benchmark):
        cipher = Cipher(KEY)
        benchmark(cipher.encrypt_string, TEXT)

    def test_hmac_hex(self, benchmark):
        cipher = Cipher(KEY)
        benchmark(cipher.hmac_hex, TEXT)
```

- [ ] **Step 7: Verify benchmarks collect and run**

Run: `.venv/bin/pytest benchmarks/bench_crypto.py --benchmark-only -q`
Expected: 5 benchmarks run and pass.

- [ ] **Step 8: Lint, typecheck**

Run: `make lint && make typecheck`
Expected: clean.

- [ ] **Step 9: Commit**

```bash
git add geode_client/crypto.py geode_client/__init__.py tests/unit/test_crypto.py benchmarks/bench_crypto.py
git commit -m "feat: add AES-256-GCM field-level encryption (Cipher)"
```

---

## Task 5: redact_dsn

**Files:**

- Modify: `geode_client/transport.py` (add `redact_dsn`)
- Modify: `geode_client/__init__.py`
- Test: `tests/unit/test_redact.py`

**Interfaces:**

- Produces: `redact_dsn(dsn: str) -> str`.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_redact.py`:

```python
"""Unit tests for redact_dsn."""

import pytest

from geode_client import redact_dsn


class TestRedactDSN:
    def test_empty(self):
        assert redact_dsn("") == ""

    def test_userinfo_user_pass(self):
        out = redact_dsn("quic://alice:s3cr3t@localhost:3141")
        assert "alice" not in out
        assert "s3cr3t" not in out
        assert "***:***@localhost:3141" in out

    def test_userinfo_user_only(self):
        out = redact_dsn("quic://alice@localhost:3141")
        assert "alice" not in out
        assert "***@localhost:3141" in out

    def test_query_params(self):
        out = redact_dsn("quic://localhost:3141?user=alice&pass=s3cr3t&graph=mydb")
        assert "alice" not in out
        assert "s3cr3t" not in out
        assert "graph=mydb" in out
        assert "user=***" in out
        assert "pass=***" in out

    def test_password_param_variants(self):
        out = redact_dsn("quic://localhost:3141?username=bob&password=hunter2")
        assert "bob" not in out
        assert "hunter2" not in out

    def test_no_creds_unchanged(self):
        dsn = "quic://localhost:3141?graph=mydb"
        assert redact_dsn(dsn) == dsn

    def test_no_scheme_bare_userinfo(self):
        out = redact_dsn("alice:s3cr3t@localhost:3141")
        assert "alice" not in out
        assert "s3cr3t" not in out

    def test_param_without_value_preserved(self):
        out = redact_dsn("quic://localhost:3141?flag&pass=x")
        assert "flag" in out
        assert "pass=***" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_redact.py -v`
Expected: FAIL — cannot import `redact_dsn`.

- [ ] **Step 3: Implement redact_dsn**

In `geode_client/transport.py`, add at module level (after `parse_dsn`):

```python
_REDACT_MASK = "***"
_CREDENTIAL_PARAMS = ("user", "username", "pass", "password")


def _redact_userinfo(uri: str) -> str:
    """Mask the user:pass@ (or user@) segment of a URI authority."""
    scheme_end = uri.find("://")
    if scheme_end == -1:
        at_idx = uri.rfind("@")
        if at_idx == -1:
            return uri
        return _redact_at_segment(uri, 0, at_idx)

    authority_start = scheme_end + 3
    authority = uri[authority_start:]
    at_idx = authority.rfind("@")
    if at_idx == -1:
        return uri
    userinfo = authority[:at_idx]
    rest = authority[at_idx:]
    masked = (
        f"{_REDACT_MASK}:{_REDACT_MASK}"
        if ":" in userinfo
        else _REDACT_MASK
    )
    return uri[:authority_start] + masked + rest


def _redact_at_segment(uri: str, start: int, at_idx: int) -> str:
    userinfo = uri[start:at_idx]
    rest = uri[at_idx:]
    masked = (
        f"{_REDACT_MASK}:{_REDACT_MASK}"
        if ":" in userinfo
        else _REDACT_MASK
    )
    return uri[:start] + masked + rest


def _redact_query_params(query: str) -> str:
    if not query:
        return query
    params = query.split("&")
    for i, param in enumerate(params):
        key, sep, _ = param.partition("=")
        if not sep:
            continue
        if key.lower() in _CREDENTIAL_PARAMS:
            params[i] = f"{key}={_REDACT_MASK}"
    return "&".join(params)


def redact_dsn(dsn: str) -> str:
    """Return ``dsn`` with credentials masked for safe logging.

    Masks URI userinfo (``user:pass@`` -> ``***:***@``) and credential
    query parameters (user, username, pass, password) to ``***``.
    """
    if not dsn:
        return dsn
    base, sep, query = dsn.partition("?")
    base = _redact_userinfo(base)
    if sep:
        return base + "?" + _redact_query_params(query)
    return base
```

- [ ] **Step 4: Export from **init**.py**

In `geode_client/__init__.py`, add `redact_dsn` to the `from .transport import (...)` block and to `__all__` (in the Transport section):

```python
    "redact_dsn",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_redact.py -v`
Expected: PASS (8 tests).

- [ ] **Step 6: Lint, typecheck**

Run: `make lint && make typecheck`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add geode_client/transport.py geode_client/__init__.py tests/unit/test_redact.py
git commit -m "feat: add redact_dsn for safe credential-masked logging"
```

---

## Task 6: Quoting helpers (quote_ident, quote_string, sanitize_graph_name)

**Files:**

- Create: `geode_client/quote.py`
- Modify: `geode_client/__init__.py`
- Test: `tests/unit/test_quote.py`

**Interfaces:**

- Produces: `InvalidIdentifierError(GeodeError)`, `InvalidStringError(GeodeError)`; `quote_ident(name: str) -> str`, `quote_string(s: str) -> str`, `sanitize_graph_name(name: str) -> str`.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_quote.py`:

```python
"""Unit tests for quoting helpers (quote.py)."""

import pytest

from geode_client import (
    InvalidIdentifierError,
    InvalidStringError,
    quote_ident,
    quote_string,
    sanitize_graph_name,
)


class TestQuoteIdent:
    @pytest.mark.parametrize(
        "name",
        ["abc", "_abc", "Abc123", "005_add_index", "a-b-c", "X1", "snake_case"],
    )
    def test_valid_returns_name(self, name):
        assert quote_ident(name) == name

    def test_empty_raises(self):
        with pytest.raises(InvalidIdentifierError):
            quote_ident("")

    def test_leading_hyphen_raises(self):
        with pytest.raises(InvalidIdentifierError):
            quote_ident("-bad")

    @pytest.mark.parametrize("name", ["bad name", "a.b", "a'b", "a;b", "a)b", "a\\b"])
    def test_forbidden_chars_raise(self, name):
        with pytest.raises(InvalidIdentifierError):
            quote_ident(name)

    def test_digit_first_allowed(self):
        assert quote_ident("9lives") == "9lives"


class TestQuoteString:
    def test_simple(self):
        assert quote_string("hello") == "'hello'"

    def test_single_quote_doubled(self):
        assert quote_string("O'Brien") == "'O''Brien'"

    def test_backslash_escaped_first(self):
        # Backslash doubled, then quotes doubled.
        assert quote_string("a\\b") == "'a\\\\b'"

    def test_backslash_then_quote(self):
        assert quote_string("a\\'b") == "'a\\\\''b'"

    def test_empty(self):
        assert quote_string("") == "''"

    @pytest.mark.parametrize("ch", ["\x00", "\x1f", "\x7f", "\n", "\t", "\r"])
    def test_control_chars_rejected(self, ch):
        with pytest.raises(InvalidStringError):
            quote_string(f"a{ch}b")

    def test_space_allowed(self):
        assert quote_string("hello world") == "'hello world'"


class TestSanitizeGraphName:
    def test_strips_forbidden(self):
        assert sanitize_graph_name("my graph!@#") == "mygraph"

    def test_keeps_allowed(self):
        assert sanitize_graph_name("My_Graph-01") == "My_Graph-01"

    def test_empty(self):
        assert sanitize_graph_name("") == ""

    def test_all_stripped(self):
        assert sanitize_graph_name("!@#$%^&*()") == ""

    def test_no_error_on_injection(self):
        # Sanitize never raises; it strips.
        assert sanitize_graph_name("g'; DROP") == "gDROP"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_quote.py -v`
Expected: FAIL — cannot import the quote symbols.

- [ ] **Step 3: Implement quote.py**

Create `geode_client/quote.py`:

```python
"""GQL quoting/escaping helpers (mirrors Go quote.go).

These produce values safe to inline into GQL admin statements. They are
distinct from ``validate.identifier`` which only validates.
"""

from .client import GeodeError


class InvalidIdentifierError(GeodeError):
    """Raised when an identifier contains forbidden characters."""


class InvalidStringError(GeodeError):
    """Raised when a string literal contains forbidden control characters."""


def quote_ident(name: str) -> str:
    """Validate ``name`` as a bare GQL identifier and return it unchanged.

    Valid identifiers contain letters, digits, underscore, and hyphen, and
    must not start with a hyphen. Digits are permitted anywhere, including
    first. Raises InvalidIdentifierError for empty or invalid input.
    """
    if not name:
        raise InvalidIdentifierError(
            "geode: identifier contains forbidden characters"
        )
    for i, ch in enumerate(name):
        if ch.isascii() and (ch.isalpha() or ch == "_"):
            continue
        if ch.isascii() and ch.isdigit():
            continue
        if ch == "-":
            if i == 0:
                raise InvalidIdentifierError(
                    "geode: identifier contains forbidden characters"
                )
            continue
        raise InvalidIdentifierError(
            "geode: identifier contains forbidden characters"
        )
    return name


def quote_string(s: str) -> str:
    """Wrap ``s`` in GQL single quotes with backslashes and quotes escaped.

    ASCII control characters (< 0x20 or == 0x7F) are rejected. Escape order:
    backslash first (``\\`` -> ``\\\\``), then single quotes (``'`` -> ``''``).
    """
    for ch in s:
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            raise InvalidStringError(
                "geode: string literal contains forbidden characters"
            )
    s = s.replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


def sanitize_graph_name(name: str) -> str:
    """Strip any character that is not alphanumeric, underscore, or hyphen.

    Unlike :func:`quote_ident`, this never raises; it removes forbidden
    characters so the result can be inlined into a USE GRAPH statement.
    """
    out = []
    for ch in name:
        if ch.isascii() and (ch.isalnum()) or ch in ("_", "-"):
            out.append(ch)
    return "".join(out)
```

> Implementer note: verify the boolean grouping in `sanitize_graph_name` — the intended predicate is `(ch.isascii() and ch.isalnum()) or ch in ("_", "-")`. Use explicit parentheses:
>
> ```python
>         if (ch.isascii() and ch.isalnum()) or ch in ("_", "-"):
>             out.append(ch)
> ```
>
> Use this parenthesized form in the final code.

- [ ] **Step 4: Export from **init**.py**

In `geode_client/__init__.py`, add:

```python
from .quote import (
    InvalidIdentifierError,
    InvalidStringError,
    quote_ident,
    quote_string,
    sanitize_graph_name,
)
```

Add to `__all__`:

```python
    # Quoting / escaping
    "quote_ident",
    "quote_string",
    "sanitize_graph_name",
    "InvalidIdentifierError",
    "InvalidStringError",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_quote.py -v`
Expected: PASS.

- [ ] **Step 6: Lint, typecheck**

Run: `make lint && make typecheck`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add geode_client/quote.py geode_client/__init__.py tests/unit/test_quote.py
git commit -m "feat: add quote_ident, quote_string, sanitize_graph_name"
```

---

## Task 7: Pool-from-DSN factory

**Files:**

- Modify: `geode_client/pool.py` (add `create_pool_from_dsn`)
- Modify: `geode_client/__init__.py`
- Test: `tests/unit/test_pool_from_dsn.py`

**Interfaces:**

- Consumes: `parse_dsn` (transport), `ConnectionPool` (pool).
- Produces: `create_pool_from_dsn(dsn: str, *, min_size: int = 1, max_size: int = 3, **kwargs) -> ConnectionPool` (built but NOT initialized — caller awaits `initialize()` or uses `async with`).

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_pool_from_dsn.py`:

```python
"""Unit tests for create_pool_from_dsn factory."""

import pytest

from geode_client import ConnectionPool, create_pool_from_dsn
from geode_client.transport import TransportType


class TestCreatePoolFromDSN:
    def test_builds_pool_from_dsn(self):
        pool = create_pool_from_dsn("quic://localhost:3141?graph=mydb")
        assert isinstance(pool, ConnectionPool)
        # localhost normalized to 127.0.0.1 by parse_dsn
        assert pool.client.host == "127.0.0.1"
        assert pool.client.port == 3141

    def test_carries_transport_type(self):
        pool = create_pool_from_dsn("grpc://localhost:50051")
        assert pool.client.config["transport_type"] == TransportType.GRPC
        assert pool.client.port == 50051

    def test_carries_tenant_role_graph(self):
        pool = create_pool_from_dsn(
            "quic://localhost:3141?tenant_id=acme&role=analyst&graph=g"
        )
        cfg = pool.client.config
        assert cfg["tenant"] == "acme"
        assert cfg["role"] == "analyst"
        assert cfg["graph"] == "g"

    def test_pool_sizing_kwargs(self):
        pool = create_pool_from_dsn(
            "quic://localhost:3141", min_size=2, max_size=7
        )
        assert pool.min_size == 2
        assert pool.max_size == 7

    def test_not_initialized(self):
        pool = create_pool_from_dsn("quic://localhost:3141")
        assert pool._initialized is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_pool_from_dsn.py -v`
Expected: FAIL — cannot import `create_pool_from_dsn`.

- [ ] **Step 3: Implement create_pool_from_dsn**

In `geode_client/pool.py`, add the import at the top:

```python
from .transport import parse_dsn
```

Add the factory at the end of the module:

```python
def create_pool_from_dsn(
    dsn: str,
    *,
    min_size: int = 1,
    max_size: int = 3,
    timeout: float = 30.0,
    **kwargs,
) -> ConnectionPool:
    """Build a ConnectionPool from a DSN string (mirrors Go NewPoolFromConfig).

    Parses ``dsn`` into a transport config and constructs an (uninitialized)
    ConnectionPool with the resulting host/port and connection parameters.
    Await ``pool.initialize()`` or use ``async with pool:`` to open it.

    Args:
        dsn: Connection DSN, e.g. ``quic://host:3141?graph=g&user=u&pass=p``.
        min_size: Minimum pool size.
        max_size: Maximum pool size.
        timeout: Acquire timeout (seconds).
        **kwargs: Extra connection params, overriding values parsed from dsn.

    Returns:
        An uninitialized ConnectionPool.
    """
    config = parse_dsn(dsn)
    conn_kwargs = {
        "transport_type": config.transport_type,
        "tls_enabled": config.tls_enabled,
        "skip_verify": config.skip_verify,
        "ca_cert": config.ca_cert,
        "client_cert": config.client_cert,
        "client_key": config.client_key,
        "server_name": config.server_name,
        "username": config.username,
        "password": config.password,
        "page_size": config.page_size,
        "hello_name": config.hello_name,
        "hello_ver": config.hello_ver,
        "conformance": config.conformance,
        "graph": config.graph,
        "tenant": config.tenant,
        "role": config.role,
    }
    conn_kwargs.update(kwargs)
    return ConnectionPool(
        host=config.host,
        port=config.port,
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        **conn_kwargs,
    )
```

- [ ] **Step 4: Export from **init**.py**

In `geode_client/__init__.py`, change the pool import line to:

```python
from .pool import ConnectionPool, create_pool, create_pool_from_dsn
```

Add to `__all__` (after `"create_pool",` if present, else after `"ConnectionPool",`):

```python
    "create_pool_from_dsn",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_pool_from_dsn.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Lint, typecheck**

Run: `make lint && make typecheck`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add geode_client/pool.py geode_client/__init__.py tests/unit/test_pool_from_dsn.py
git commit -m "feat: add create_pool_from_dsn factory"
```

---

## Task 8: Errors module — DriverError, NoRowsError, query_row

**Files:**

- Create: `geode_client/errors.py`
- Modify: `geode_client/client.py` (raise DriverError from query; add `query_row`)
- Modify: `geode_client/__init__.py`
- Test: `tests/unit/test_errors.py`, `tests/unit/test_query_row.py`

**Interfaces:**

- Produces:
  - `geode_client/errors.py`: status constants `STATUS_AUTH="28000"`, `STATUS_SYNTAX="42000"`, `STATUS_SERIALIZATION="40001"`, `STATUS_DEADLOCK="40502"`, `STATUS_PASSWORD_RESET="08P01"`; `DriverError(GeodeError)` with `code: str`, `status_class: str`, `message: str`, `is_retryable() -> bool`; `NoRowsError(GeodeError)`; `is_auth_error(exc) -> bool`, `is_syntax_error(exc) -> bool`, `is_retryable_error(exc) -> bool`.
  - `Connection.query_row(text, params=None) -> Dict[str, Value]` raising `NoRowsError` when empty (alias `fetch_one`).

> Note: `DriverError` must subclass `GeodeError` (defined in `client.py`). To avoid a circular import (`client.py` will import from `errors.py`), `errors.py` imports `GeodeError` from `client.py`, and `client.py` imports names from `errors.py` *after* `GeodeError` is defined (import near other local imports — `GeodeError` is defined at module top of client.py before the import executes only if placed below the class). Simplest: define `GeodeError` hierarchy where it is, and in `errors.py` do `from .client import GeodeError`. `client.py` imports `errors` lazily inside methods OR at top after class definitions. Use a top-of-module import in `errors.py` and a top import in `client.py` that refers to `errors` — Python resolves this because `errors.py` only needs `GeodeError` which is defined early in `client.py`. To be safe, in `client.py` import errors symbols at the point of use (function-local import) for `query`/`query_row`. This plan uses function-local imports in client.py to guarantee no cycle.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_errors.py`:

```python
"""Unit tests for the errors module: DriverError + classifiers."""

import pytest

from geode_client import (
    DriverError,
    GeodeError,
    NoRowsError,
    is_auth_error,
    is_retryable_error,
    is_syntax_error,
)


class TestDriverError:
    def test_is_geode_error(self):
        assert issubclass(DriverError, GeodeError)

    def test_fields(self):
        e = DriverError(code="US001", status_class="42000", message="bad")
        assert e.code == "US001"
        assert e.status_class == "42000"
        assert e.message == "bad"

    def test_str_includes_code_and_message(self):
        e = DriverError(code="US001", status_class="42000", message="bad")
        assert "US001" in str(e)
        assert "bad" in str(e)

    def test_retryable_serialization(self):
        assert DriverError(code="x", status_class="40001").is_retryable()

    def test_retryable_deadlock(self):
        assert DriverError(code="x", status_class="40502").is_retryable()

    def test_not_retryable_syntax(self):
        assert not DriverError(code="x", status_class="42000").is_retryable()


class TestClassifiers:
    def test_is_auth_error_28000(self):
        assert is_auth_error(DriverError(code="x", status_class="28000"))

    def test_is_auth_error_08P01(self):
        assert is_auth_error(DriverError(code="x", status_class="08P01"))

    def test_is_auth_error_false(self):
        assert not is_auth_error(DriverError(code="x", status_class="42000"))

    def test_is_auth_error_none(self):
        assert is_auth_error(None) is False

    def test_is_auth_error_non_driver(self):
        assert is_auth_error(ValueError("x")) is False

    def test_is_syntax_error_true(self):
        assert is_syntax_error(DriverError(code="x", status_class="42000"))

    def test_is_syntax_error_false(self):
        assert not is_syntax_error(DriverError(code="x", status_class="28000"))

    def test_is_retryable_error_true(self):
        assert is_retryable_error(DriverError(code="x", status_class="40001"))

    def test_is_retryable_error_false(self):
        assert not is_retryable_error(DriverError(code="x", status_class="42000"))

    def test_is_retryable_error_non_driver(self):
        assert is_retryable_error(ValueError("x")) is False


class TestNoRowsError:
    def test_is_geode_error(self):
        assert issubclass(NoRowsError, GeodeError)
```

Create `tests/unit/test_query_row.py`:

```python
"""Unit tests for Connection.query_row / fetch_one."""

import pytest

from geode_client import NoRowsError, Value, ValueKind
from geode_client.client import Column, Connection, Page


def _conn_with_page(page):
    conn = Connection(host="h", port=1)
    conn._connected = True

    async def fake_query(text, params=None, page_size=None):
        async def empty_pager():
            return
            yield  # pragma: no cover

        return page, empty_pager

    conn.query = fake_query  # type: ignore[method-assign]
    return conn


class TestQueryRow:
    @pytest.mark.asyncio
    async def test_returns_first_row(self):
        row = {"x": Value(kind=ValueKind.INT, int_value=42)}
        page = Page(columns=[Column(name="x", type="INT")], rows=[row], final=True)
        conn = _conn_with_page(page)
        result = await conn.query_row("RETURN 1 AS x")
        assert result["x"].as_int == 42

    @pytest.mark.asyncio
    async def test_raises_no_rows_when_empty(self):
        page = Page(columns=[Column(name="x", type="INT")], rows=[], final=True)
        conn = _conn_with_page(page)
        with pytest.raises(NoRowsError):
            await conn.query_row("MATCH (n) RETURN n")

    @pytest.mark.asyncio
    async def test_fetch_one_alias(self):
        row = {"x": Value(kind=ValueKind.INT, int_value=7)}
        page = Page(columns=[Column(name="x", type="INT")], rows=[row], final=True)
        conn = _conn_with_page(page)
        result = await conn.fetch_one("RETURN 7 AS x")
        assert result["x"].as_int == 7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_errors.py tests/unit/test_query_row.py -v`
Expected: FAIL — symbols not importable; `query_row`/`fetch_one` missing.

- [ ] **Step 3: Implement errors.py**

Create `geode_client/errors.py`:

```python
"""Geode error types and classifiers (mirrors Go errors.go).

DriverError carries an ISO/IEC 39075 status class used to classify
authentication, syntax, and retryable (serialization/deadlock) failures.
"""

from typing import Optional

from .client import GeodeError

# ISO/IEC 39075 status class constants.
STATUS_SUCCESS = "00000"
STATUS_NO_DATA = "02000"
STATUS_TRANSACTION_STATE = "25000"
STATUS_AUTH = "28000"
STATUS_PASSWORD_RESET = "08P01"  # Geode-specific
STATUS_SERIALIZATION = "40001"
STATUS_DEADLOCK = "40502"
STATUS_SYNTAX = "42000"

_RETRYABLE_CLASSES = (STATUS_SERIALIZATION, STATUS_DEADLOCK)
_AUTH_CLASSES = (STATUS_AUTH, STATUS_PASSWORD_RESET)


class DriverError(GeodeError):
    """An error returned by the Geode server with an ISO/IEC 39075 status."""

    def __init__(
        self,
        code: str = "",
        status_class: str = "",
        message: str = "",
    ) -> None:
        self.code = code
        self.status_class = status_class
        self.message = message
        if message:
            super().__init__(f"{code}: {message}" if code else message)
        else:
            super().__init__(code)

    def is_retryable(self) -> bool:
        """Whether the operation may be retried (serialization/deadlock)."""
        return self.status_class in _RETRYABLE_CLASSES


class NoRowsError(GeodeError):
    """Raised when a single-row accessor finds no rows (Go: sql.ErrNoRows)."""


def is_auth_error(exc: Optional[BaseException]) -> bool:
    """Whether ``exc`` is an authentication/authorization failure."""
    if not isinstance(exc, DriverError):
        return False
    return exc.status_class in _AUTH_CLASSES


def is_syntax_error(exc: Optional[BaseException]) -> bool:
    """Whether ``exc`` is a GQL parse/syntax error (status 42000)."""
    if not isinstance(exc, DriverError):
        return False
    return exc.status_class == STATUS_SYNTAX


def is_retryable_error(exc: Optional[BaseException]) -> bool:
    """Whether ``exc`` is a retryable Geode error."""
    if not isinstance(exc, DriverError):
        return False
    return exc.is_retryable()
```

- [ ] **Step 4: Raise DriverError from query + add query_row**

In `geode_client/client.py`, change the two query-error raise sites. Both currently do:

```python
            raise QueryError(f"{exec_resp.error.code}: {exec_resp.error.message}")
```

Replace each with a DriverError that captures the status class when present (function-local import to avoid circular import):

```python
            from .errors import DriverError

            status_class = ""
            if exec_resp.HasField("status"):
                status_class = exec_resp.status.status_class
            raise DriverError(
                code=exec_resp.error.code,
                status_class=status_class,
                message=exec_resp.error.message,
            )
```

Apply to both occurrences (the first-response path near "Check for error" and the read_next path). `DriverError` subclasses `GeodeError`, so existing `except (QueryError, GeodeError)` handlers still catch it.

Then add the single-row accessor methods to `Connection` (after `query`):

```python
    async def query_row(
        self,
        text: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, "Value"]:
        """Execute a query and return its first row.

        Raises NoRowsError if the result set is empty (mirrors Go ErrNoRows).
        """
        from .errors import NoRowsError

        page, _ = await self.query(text, params)
        if not page.rows:
            raise NoRowsError("geode: no rows in result set")
        return page.rows[0]

    async def fetch_one(
        self,
        text: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, "Value"]:
        """Alias for :meth:`query_row`."""
        return await self.query_row(text, params)
```

- [ ] **Step 5: Export from **init**.py**

In `geode_client/__init__.py`, add:

```python
from .errors import (
    DriverError,
    NoRowsError,
    is_auth_error,
    is_retryable_error,
    is_syntax_error,
)
```

Add to `__all__` (Errors section):

```python
    "DriverError",
    "NoRowsError",
    "is_auth_error",
    "is_syntax_error",
    "is_retryable_error",
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_errors.py tests/unit/test_query_row.py -v`
Expected: PASS.

- [ ] **Step 7: Lint, typecheck, full unit run**

Run: `make lint && make typecheck && .venv/bin/pytest tests/unit/ -q`
Expected: clean; all pass (verify existing query error tests still pass — DriverError message format `"code: message"` matches old QueryError format).

- [ ] **Step 8: Commit**

```bash
git add geode_client/errors.py geode_client/client.py geode_client/__init__.py tests/unit/test_errors.py tests/unit/test_query_row.py
git commit -m "feat: add DriverError, NoRowsError, classifiers, and query_row"
```

---

## Task 9: Node / Edge / Path typed values + converters

**Files:**

- Modify: `geode_client/types.py` (add dataclasses + converters)
- Modify: `geode_client/__init__.py`
- Test: `tests/unit/test_graph_types.py`

**Interfaces:**

- Consumes: `Value`, `ValueKind` (types). NODE/EDGE values are `Value` of kind NODE/EDGE whose `object_value` holds keys: node -> `id`(INT), `labels`(ARRAY of STRING), `properties`(OBJECT); edge -> `id`, `start_node`, `end_node`(INT), `type`(STRING), `properties`(OBJECT); path -> `nodes`(ARRAY of NODE Values), `edges`(ARRAY of EDGE Values). This matches `Connection._build_node_value`/`_build_edge_value` in client.py.
- Produces: `Node{id:int, labels:List[str], properties:Dict[str,Any]}`, `Edge{id:int, start_node:int, end_node:int, type:str, properties:Dict[str,Any]}`, `Path{nodes:List[Node], edges:List[Edge]}`; `as_node(v: Value) -> Node`, `as_edge(v: Value) -> Edge`, `as_path(v: Value) -> Path`. Each raises `ValueError` if `v` is not the expected kind.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_graph_types.py`:

```python
"""Unit tests for Node/Edge/Path typed values and converters."""

import pytest

from geode_client import Edge, Node, Path, Value, ValueKind, as_edge, as_node, as_path


def _node_value(node_id, labels, props):
    return Value(
        kind=ValueKind.NODE,
        object_value={
            "id": Value(kind=ValueKind.INT, int_value=node_id),
            "labels": Value(
                kind=ValueKind.ARRAY,
                array_value=[
                    Value(kind=ValueKind.STRING, str_value=label) for label in labels
                ],
            ),
            "properties": Value(
                kind=ValueKind.OBJECT,
                object_value={
                    k: Value(kind=ValueKind.STRING, str_value=v)
                    for k, v in props.items()
                },
            ),
        },
    )


def _edge_value(edge_id, start, end, etype, props):
    return Value(
        kind=ValueKind.EDGE,
        object_value={
            "id": Value(kind=ValueKind.INT, int_value=edge_id),
            "start_node": Value(kind=ValueKind.INT, int_value=start),
            "end_node": Value(kind=ValueKind.INT, int_value=end),
            "type": Value(kind=ValueKind.STRING, str_value=etype),
            "properties": Value(
                kind=ValueKind.OBJECT,
                object_value={
                    k: Value(kind=ValueKind.STRING, str_value=v)
                    for k, v in props.items()
                },
            ),
        },
    )


class TestAsNode:
    def test_basic(self):
        node = as_node(_node_value(1, ["Person", "User"], {"name": "Alice"}))
        assert isinstance(node, Node)
        assert node.id == 1
        assert node.labels == ["Person", "User"]
        assert node.properties == {"name": "Alice"}

    def test_wrong_kind_raises(self):
        with pytest.raises(ValueError):
            as_node(Value(kind=ValueKind.INT, int_value=1))


class TestAsEdge:
    def test_basic(self):
        edge = as_edge(_edge_value(10, 1, 2, "KNOWS", {"since": "2020"}))
        assert isinstance(edge, Edge)
        assert edge.id == 10
        assert edge.start_node == 1
        assert edge.end_node == 2
        assert edge.type == "KNOWS"
        assert edge.properties == {"since": "2020"}

    def test_wrong_kind_raises(self):
        with pytest.raises(ValueError):
            as_edge(Value(kind=ValueKind.STRING, str_value="x"))


class TestAsPath:
    def test_nested_assembly(self):
        n1 = _node_value(1, ["Person"], {"name": "A"})
        n2 = _node_value(2, ["Person"], {"name": "B"})
        e1 = _edge_value(10, 1, 2, "KNOWS", {})
        path_val = Value(
            kind=ValueKind.PATH,
            object_value={
                "nodes": Value(kind=ValueKind.ARRAY, array_value=[n1, n2]),
                "edges": Value(kind=ValueKind.ARRAY, array_value=[e1]),
            },
        )
        path = as_path(path_val)
        assert isinstance(path, Path)
        assert [n.id for n in path.nodes] == [1, 2]
        assert len(path.edges) == 1
        assert path.edges[0].type == "KNOWS"
        assert isinstance(path.nodes[0], Node)
        assert isinstance(path.edges[0], Edge)

    def test_empty_path(self):
        path_val = Value(
            kind=ValueKind.PATH,
            object_value={
                "nodes": Value(kind=ValueKind.ARRAY, array_value=[]),
                "edges": Value(kind=ValueKind.ARRAY, array_value=[]),
            },
        )
        path = as_path(path_val)
        assert path.nodes == []
        assert path.edges == []

    def test_wrong_kind_raises(self):
        with pytest.raises(ValueError):
            as_path(Value(kind=ValueKind.OBJECT, object_value={}))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_graph_types.py -v`
Expected: FAIL — cannot import `Node`/`Edge`/`Path`/`as_node`/`as_edge`/`as_path`.

- [ ] **Step 3: Implement dataclasses + converters in types.py**

In `geode_client/types.py`, add at the end of the module (after `decode_value`):

```python
@dataclass
class Node:
    """Typed representation of a Geode graph node value."""

    id: int = 0
    labels: List[str] = None  # type: ignore[assignment]
    properties: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.labels is None:
            self.labels = []
        if self.properties is None:
            self.properties = {}


@dataclass
class Edge:
    """Typed representation of a Geode graph edge (relationship) value."""

    id: int = 0
    start_node: int = 0
    end_node: int = 0
    type: str = ""
    properties: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.properties is None:
            self.properties = {}


@dataclass
class Path:
    """Typed representation of a Geode graph path value."""

    nodes: List[Node] = None  # type: ignore[assignment]
    edges: List[Edge] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.nodes is None:
            self.nodes = []
        if self.edges is None:
            self.edges = []


def _value_to_py(value: "Value") -> Any:
    """Convert a Value to a plain Python value via its raw_value property."""
    return value.raw_value


def as_node(value: "Value") -> Node:
    """Convert a NODE-kind Value to a typed Node.

    Raises ValueError if ``value`` is not a NODE value.
    """
    if value.kind != ValueKind.NODE or value.object_value is None:
        raise ValueError(f"Cannot convert {value.kind} to Node")
    obj = value.object_value
    node_id = obj["id"].int_value if "id" in obj else 0
    labels: List[str] = []
    if "labels" in obj and obj["labels"].array_value:
        labels = [item.str_value for item in obj["labels"].array_value]
    props: Dict[str, Any] = {}
    if "properties" in obj and obj["properties"].object_value:
        props = {k: v.raw_value for k, v in obj["properties"].object_value.items()}
    return Node(id=node_id, labels=labels, properties=props)


def as_edge(value: "Value") -> Edge:
    """Convert an EDGE-kind Value to a typed Edge.

    Raises ValueError if ``value`` is not an EDGE value.
    """
    if value.kind != ValueKind.EDGE or value.object_value is None:
        raise ValueError(f"Cannot convert {value.kind} to Edge")
    obj = value.object_value
    edge_id = obj["id"].int_value if "id" in obj else 0
    start = obj["start_node"].int_value if "start_node" in obj else 0
    end = obj["end_node"].int_value if "end_node" in obj else 0
    etype = obj["type"].str_value if "type" in obj else ""
    props: Dict[str, Any] = {}
    if "properties" in obj and obj["properties"].object_value:
        props = {k: v.raw_value for k, v in obj["properties"].object_value.items()}
    return Edge(
        id=edge_id, start_node=start, end_node=end, type=etype, properties=props
    )


def as_path(value: "Value") -> Path:
    """Convert a PATH-kind Value to a typed Path.

    Recursively converts nested node and edge Values. Raises ValueError if
    ``value`` is not a PATH value.
    """
    if value.kind != ValueKind.PATH or value.object_value is None:
        raise ValueError(f"Cannot convert {value.kind} to Path")
    obj = value.object_value
    nodes: List[Node] = []
    if "nodes" in obj and obj["nodes"].array_value:
        nodes = [as_node(n) for n in obj["nodes"].array_value]
    edges: List[Edge] = []
    if "edges" in obj and obj["edges"].array_value:
        edges = [as_edge(e) for e in obj["edges"].array_value]
    return Path(nodes=nodes, edges=edges)
```

> Implementer note: `_value_to_py` is a convenience that is currently unused; omit it to avoid a lint "unused function" issue. The converters use `v.raw_value` directly. Do NOT add `_value_to_py` to the file.

- [ ] **Step 4: Export from **init**.py**

In `geode_client/__init__.py`, change the types import to:

```python
from .types import (
    Edge,
    Node,
    Path,
    Range,
    Value,
    ValueKind,
    as_edge,
    as_node,
    as_path,
)
```

Add to `__all__` (Result types section):

```python
    "Node",
    "Edge",
    "Path",
    "as_node",
    "as_edge",
    "as_path",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_graph_types.py -v`
Expected: PASS.

- [ ] **Step 6: Lint, typecheck**

Run: `make lint && make typecheck`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add geode_client/types.py geode_client/__init__.py tests/unit/test_graph_types.py
git commit -m "feat: add Node/Edge/Path typed values and as_node/as_edge/as_path"
```

---

## Task 10: format_dsn round-trip

**Files:**

- Modify: `geode_client/transport.py` (add `format_dsn`)
- Modify: `geode_client/__init__.py`
- Test: `tests/unit/test_format_dsn.py`
- Property test: `tests/property/test_hypothesis.py` (add a round-trip property)

**Interfaces:**

- Consumes: `TransportConfig`, `TransportType`, `parse_dsn`.
- Produces: `format_dsn(config: TransportConfig) -> str` — inverse of `parse_dsn`. Emits scheme, `host:port` (IPv6 bracketed), credentials in userinfo (`user:pass@`; password-only via `pass=` query param), and non-default params: `page_size` (if not 1000), `hello_name` (if not "geode-python"), `hello_ver` (if not "0.1.0"), `conformance` (if not "min"), `ca`/`cert`/`key`, `insecure_tls_skip_verify=true` (if skip_verify), `tls=0` (if not tls_enabled), `graph`, `tenant`, `role`.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_format_dsn.py`:

```python
"""Unit tests for format_dsn (inverse of parse_dsn)."""

import pytest

from geode_client import format_dsn, parse_dsn
from geode_client.transport import TransportConfig, TransportType


class TestFormatDSN:
    def test_minimal(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC, host="127.0.0.1", port=3141
        )
        assert format_dsn(cfg) == "quic://127.0.0.1:3141"

    def test_grpc_scheme(self):
        cfg = TransportConfig(
            transport_type=TransportType.GRPC, host="h", port=50051
        )
        assert format_dsn(cfg).startswith("grpc://h:50051")

    def test_emits_non_default_params(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC,
            host="h",
            port=3141,
            graph="mydb",
            tenant="acme",
            role="analyst",
        )
        out = format_dsn(cfg)
        assert "graph=mydb" in out
        assert "tenant=acme" in out
        assert "role=analyst" in out

    def test_omits_default_params(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC,
            host="h",
            port=3141,
            page_size=1000,  # default
            conformance="min",  # default
        )
        out = format_dsn(cfg)
        assert "page_size" not in out
        assert "conformance" not in out

    def test_credentials_userinfo(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC,
            host="h",
            port=3141,
            username="alice",
            password="s3cr3t",
        )
        out = format_dsn(cfg)
        assert out.startswith("quic://alice:s3cr3t@h:3141")

    def test_password_only_query_param(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC,
            host="h",
            port=3141,
            password="s3cr3t",
        )
        out = format_dsn(cfg)
        assert "@" not in out
        assert "pass=s3cr3t" in out

    def test_skip_verify_and_tls_disabled(self):
        cfg = TransportConfig(
            transport_type=TransportType.GRPC,
            host="h",
            port=50051,
            skip_verify=True,
            tls_enabled=False,
        )
        out = format_dsn(cfg)
        assert "insecure_tls_skip_verify=true" in out
        assert "tls=0" in out

    def test_ipv6_bracketed(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC, host="::1", port=3141
        )
        out = format_dsn(cfg)
        assert "[::1]:3141" in out


class TestRoundTrip:
    def test_parse_format_parse(self):
        original = "quic://alice:s3cr3t@127.0.0.1:3141?graph=mydb&tenant=acme&role=analyst"
        cfg = parse_dsn(original)
        formatted = format_dsn(cfg)
        cfg2 = parse_dsn(formatted)
        assert cfg2.host == cfg.host
        assert cfg2.port == cfg.port
        assert cfg2.transport_type == cfg.transport_type
        assert cfg2.username == cfg.username
        assert cfg2.password == cfg.password
        assert cfg2.graph == cfg.graph
        assert cfg2.tenant == cfg.tenant
        assert cfg2.role == cfg.role
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_format_dsn.py -v`
Expected: FAIL — cannot import `format_dsn`.

- [ ] **Step 3: Implement format_dsn**

In `geode_client/transport.py`, add module-level default constants near the top (after `MAX_MESSAGE_SIZE`):

```python
# Defaults used to decide which params format_dsn emits (parity with Go FormatDSN).
_DEFAULT_PAGE_SIZE = 1000
_DEFAULT_HELLO_NAME = "geode-python"
_DEFAULT_HELLO_VER = "0.1.0"
_DEFAULT_CONFORMANCE = "min"
```

Add after `redact_dsn` (Task 5):

```python
def _format_host_port(host: str, port: int) -> str:
    """Join host and port, bracketing IPv6 literals."""
    if ":" in host and not host.startswith("["):
        return f"[{host}]:{port}"
    return f"{host}:{port}"


def format_dsn(config: "TransportConfig") -> str:
    """Serialise ``config`` back into a DSN string (inverse of parse_dsn).

    Only non-default values are emitted as query parameters. Credentials are
    embedded in the userinfo segment (scheme://user:pass@host:port); a
    password without a username is emitted as a ``pass`` query parameter.
    """
    from urllib.parse import quote, urlencode

    scheme = config.transport_type.value
    host_port = _format_host_port(config.host, config.port)

    params: list[tuple[str, str]] = []
    if config.page_size and config.page_size != _DEFAULT_PAGE_SIZE:
        params.append(("page_size", str(config.page_size)))
    if config.hello_name and config.hello_name != _DEFAULT_HELLO_NAME:
        params.append(("hello_name", config.hello_name))
    if config.hello_ver and config.hello_ver != _DEFAULT_HELLO_VER:
        params.append(("hello_ver", config.hello_ver))
    if config.conformance and config.conformance != _DEFAULT_CONFORMANCE:
        params.append(("conformance", config.conformance))
    if config.ca_cert:
        params.append(("ca", config.ca_cert))
    if config.client_cert:
        params.append(("cert", config.client_cert))
    if config.client_key:
        params.append(("key", config.client_key))
    if config.skip_verify:
        params.append(("insecure_tls_skip_verify", "true"))
    if not config.tls_enabled:
        params.append(("tls", "0"))
    if config.graph:
        params.append(("graph", config.graph))
    if config.tenant:
        params.append(("tenant", config.tenant))
    if config.role:
        params.append(("role", config.role))

    userinfo = ""
    if config.username and config.password:
        userinfo = f"{quote(config.username, safe='')}:{quote(config.password, safe='')}@"
    elif config.username:
        userinfo = f"{quote(config.username, safe='')}@"
    elif config.password:
        params.append(("pass", config.password))

    dsn = f"{scheme}://{userinfo}{host_port}"
    if params:
        dsn += "?" + urlencode(params)
    return dsn
```

- [ ] **Step 4: Export from **init**.py**

In `geode_client/__init__.py`, add `format_dsn` to the `from .transport import (...)` block and to `__all__` (Transport section):

```python
    "format_dsn",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_format_dsn.py -v`
Expected: PASS.

- [ ] **Step 6: Add Hypothesis round-trip property test**

In `tests/property/test_hypothesis.py`, add at the end of the file a new test class:

```python
class TestFormatDSNRoundTrip:
    """format_dsn(parse_dsn(...)) preserves core fields."""

    @given(
        host=st.from_regex(r"[a-z][a-z0-9.\-]{0,20}", fullmatch=True),
        port=ports,
        graph=st.from_regex(r"[a-zA-Z0-9_\-]{0,20}", fullmatch=True),
        tenant=st.from_regex(r"[a-zA-Z0-9_\-]{0,20}", fullmatch=True),
        role=st.from_regex(r"[a-zA-Z0-9_\-]{0,20}", fullmatch=True),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_round_trip_preserves_fields(self, host, port, graph, tenant, role):
        from geode_client import format_dsn, parse_dsn
        from geode_client.transport import TransportConfig, TransportType

        cfg = TransportConfig(
            transport_type=TransportType.QUIC,
            host=host,
            port=port,
            graph=graph,
            tenant=tenant,
            role=role,
        )
        cfg2 = parse_dsn(format_dsn(cfg))
        assert cfg2.host == ("127.0.0.1" if host == "localhost" else host)
        assert cfg2.port == port
        assert cfg2.graph == graph
        assert cfg2.tenant == tenant
        assert cfg2.role == role
```

- [ ] **Step 7: Run property test**

Run: `.venv/bin/pytest tests/property/test_hypothesis.py::TestFormatDSNRoundTrip -v`
Expected: PASS.

- [ ] **Step 8: Lint, typecheck**

Run: `make lint && make typecheck`
Expected: clean.

- [ ] **Step 9: Commit**

```bash
git add geode_client/transport.py geode_client/__init__.py tests/unit/test_format_dsn.py tests/property/test_hypothesis.py
git commit -m "feat: add format_dsn with parse_dsn round-trip property test"
```

---

## Task 11: RetryPolicy + retry

**Files:**

- Create: `geode_client/retry.py`
- Modify: `geode_client/__init__.py`
- Test: `tests/unit/test_retry.py`

> **Execution Order:** Implement this task BEFORE Task 3 (batch_exec uses retry) and after Task 8 (retry uses `is_retryable_error`). Recommended order: 1, 2, 8, 11, 3, 4, 5, 6, 7, 9, 10, 12.

**Interfaces:**

- Consumes: `is_retryable_error` (Task 8).
- Produces: `RetryPolicy{max_attempts:int=3, initial_backoff:float=1.0, max_backoff:float=30.0, multiplier:float=2.0}` with `backoff(attempt:int)->float`; `default_retry_policy() -> RetryPolicy`; async `retry(fn: Callable[[], Awaitable[T]], policy: RetryPolicy) -> T`.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_retry.py`:

```python
"""Unit tests for RetryPolicy and retry."""

import asyncio

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
    async def fake_sleep(_):
        return None

    monkeypatch.setattr("geode_client.retry.asyncio.sleep", fake_sleep)


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/unit/test_retry.py -v`
Expected: FAIL — cannot import retry symbols.

- [ ] **Step 3: Implement retry.py**

Create `geode_client/retry.py`:

```python
"""Retry policy and async retry helper (mirrors Go retry.go).

Defaults: 3 attempts, 1s initial backoff, 30s max backoff, 2.0x multiplier.
Only retryable Geode errors (serialization/deadlock) are retried.
"""

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from .errors import is_retryable_error

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
```

- [ ] **Step 4: Export from **init**.py**

In `geode_client/__init__.py`, add:

```python
from .retry import RetryPolicy, default_retry_policy, retry
```

Add to `__all__` (new Retry section):

```python
    # Retry
    "RetryPolicy",
    "default_retry_policy",
    "retry",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/unit/test_retry.py -v`
Expected: PASS.

- [ ] **Step 6: Lint, typecheck**

Run: `make lint && make typecheck`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add geode_client/retry.py geode_client/__init__.py tests/unit/test_retry.py
git commit -m "feat: add RetryPolicy, default_retry_policy, and async retry"
```

---

## Task 12: Classifiers integration verification + integration test authoring

> The classifiers `is_auth_error`/`is_syntax_error` are implemented in Task 8. This task adds the integration test file (collectable without a server) covering the parity features end-to-end against a live server, and a final full verification.

**Files:**

- Create: `tests/integration/test_parity.py`
- Test: collection-only verification

**Interfaces:**

- Consumes: all prior tasks' public API; integration fixtures `client`, `connection` from `tests/integration/conftest.py`.

- [ ] **Step 1: Write the integration test (collectable, server-gated)**

Create `tests/integration/test_parity.py`:

```python
"""Integration tests for driver-parity features.

These require a running Geode server (or Docker). They are marked
`integration` (auto-applied by conftest) and skipped without a server, but
must import and collect cleanly under pytest.
"""

import pytest

from geode_client import (
    Cipher,
    NoRowsError,
    Statement,
    as_node,
    create_pool_from_dsn,
    parse_schema_fs,
)
from geode_client.types import ValueKind


@pytest.mark.asyncio
class TestParityIntegration:
    async def test_query_row_returns_row(self, connection):
        row = await connection.query_row("RETURN 1 AS x")
        assert row["x"].as_int == 1

    async def test_query_row_no_rows_raises(self, connection):
        with pytest.raises(NoRowsError):
            await connection.query_row(
                "MATCH (n:DoesNotExist12345) RETURN n LIMIT 1"
            )

    async def test_batch_exec_single_transaction(self, connection):
        await connection.batch_exec(
            [
                Statement("CREATE (:ParityTest {n: 1})"),
                Statement("CREATE (:ParityTest {n: 2})"),
            ]
        )
        page, _ = await connection.query(
            "MATCH (p:ParityTest) RETURN count(p) AS c"
        )
        assert page.rows[0]["c"].as_int >= 2

    async def test_pipeline_exec(self, connection):
        stmts = [Statement(f"CREATE (:PipeTest {{i: {i}}})") for i in range(50)]
        await connection.pipeline_exec(stmts, chunk_size=10, max_workers=4)

    async def test_as_node_conversion(self, connection):
        await connection.execute("CREATE (:NodeConv {name: 'Alice'})")
        page, _ = await connection.query(
            "MATCH (n:NodeConv) RETURN n LIMIT 1"
        )
        value = page.rows[0]["n"]
        if value.kind == ValueKind.NODE:
            node = as_node(value)
            assert "NodeConv" in node.labels


def test_parse_schema_fs_with_tmp(tmp_path):
    """parse_schema_fs is server-independent; exercise it during collection."""
    (tmp_path / "schema.gql").write_text("CREATE (:Seed {ok: true});")
    stmts = parse_schema_fs(tmp_path)
    assert stmts and stmts[0].query.startswith("CREATE")


def test_cipher_round_trip_no_server():
    """Crypto is server-independent."""
    cipher = Cipher(b"0123456789abcdef0123456789abcdef")
    assert cipher.decrypt_string(cipher.encrypt_string("hello")) == "hello"


def test_create_pool_from_dsn_builds_without_connecting():
    """Factory builds an uninitialized pool without contacting a server."""
    pool = create_pool_from_dsn("quic://localhost:3141?graph=g")
    assert pool.client.port == 3141
```

- [ ] **Step 2: Verify integration tests collect cleanly (no server)**

Run: `.venv/bin/pytest tests/integration/test_parity.py --collect-only -q`
Expected: collection succeeds (all items listed, no import errors).

- [ ] **Step 3: Verify server-independent tests pass without a server**

Run: `.venv/bin/pytest tests/integration/test_parity.py -k "no_server or tmp or without_connecting" -p no:cacheprovider -q`
Expected: the three non-fixture tests pass; fixture-based async tests are not selected.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_parity.py
git commit -m "test: add driver-parity integration tests (server-gated, collectable)"
```

---

## Final Verification (after all tasks)

- [ ] **Step 1: Lint**

Run: `make lint`
Expected: `All checks passed!`

- [ ] **Step 2: Format check**

Run: `make fmt-check`
Expected: clean. (If it fails, run `make fmt` then re-commit formatting.)

- [ ] **Step 3: Typecheck**

Run: `make typecheck`
Expected: `Success: no issues found`.

- [ ] **Step 4: Unit tests**

Run: `make test-unit`
Expected: all pass (baseline 735 + new tests).

- [ ] **Step 5: Property tests**

Run: `make test-property`
Expected: all pass (baseline 50 + new round-trip property).

- [ ] **Step 6: Benchmarks compile + run**

Run: `make bench`
Expected: all benchmarks (existing + crypto) run and pass.

- [ ] **Step 7: Integration collection**

Run: `.venv/bin/pytest tests/integration/ --collect-only -q`
Expected: clean collection (no server required).

---

## Self-Review Notes

- **Spec coverage:** Task 1 (HELLO tenant/role), Task 2 (parse_schema_fs), Task 3 (Statement/batch_exec/pipeline_exec), Task 4 (crypto FLE), Task 5 (redact_dsn), Task 6 (quote helpers), Task 7 (pool-from-DSN), Task 8 (NoRowsError/query_row + DriverError), Task 9 (Node/Edge/Path + converters), Task 10 (format_dsn + property), Task 11 (RetryPolicy/retry), Task 12 (is_auth_error/is_syntax_error verified in Task 8 tests + integration). All 12 Delta items covered. Proto `role` field already regenerated in a pre-task foundational commit.
- **Type consistency:** `Statement(query, params)` used consistently in Tasks 2, 3, 12. `DriverError(code, status_class, message)` consistent in Tasks 3, 8, 11. `RetryPolicy` field names (`max_attempts`, `initial_backoff`, `max_backoff`, `multiplier`) consistent in Tasks 11 and used by Task 3.
- **No placeholders:** every code step contains complete code.
- **Execution order dependency:** Tasks 8 and 11 must precede Task 3. Recommended order: 1, 2, 8, 11, 3, 4, 5, 6, 7, 9, 10, 12.

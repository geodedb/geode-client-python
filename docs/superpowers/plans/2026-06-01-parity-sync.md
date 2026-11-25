# Python Client Parity-Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. TDD: failing test first, then minimal implementation.

**Goal:** Bring the Python Geode client to feature/behavior parity with the Go (`v0.1.22` + unreleased `main`) and Zig (`v0.2.10`) references, ship on `main` with a version bump and green CI.

**Architecture:** Python client already matches the reference transport stack (QUIC default via `aioquic`, optional gRPC via `grpcio`, ALPN `geode/1`, length-prefixed protobuf). It already has graph-native Node/Edge/Path (object-shaped Values), pool, auth, query builder, validation. The main parity gaps are **typed error predicates / SQLSTATE constants** (Go has `IsAuthError`/`IsSyntaxError`/`IsRetryableError`; Python only raises string `QueryError`) and finalizing the in-flight reliability WIP (connect retry, serial pool teardown, longer HELLO timeout).

**Tech Stack:** Python 3.12+, `aioquic`/`grpcio`, `pytest`/`pytest-asyncio`, GitLab CI (`python-lint` ruff, inline `mypy`, `python-test`, `python-coverage` threshold 80).

**Reference sources to mirror (read these):**
- Go errors: `../geode-client-go/errors.go` (status classes 28000/42000/40001/40P01/40502, `IsAuthError` also matches `08P01`, `IsRetryableError`, `IsSyntaxError`).
- Existing Node client: `../geode-client-nodejs/src/errors.ts` (`isRetryableError`, `isDriverError`, `StatusClass` map).
- Python current errors: `geode_client/errors.py`, no-data check `client.py:_is_no_data_response`.

---

## Baseline (verified 2026-06-01)
- Branch `codex/client-parity-sync`. `pytest tests/unit/` = 736 passed. Integration `test_basic_operations.py` = 12 passed vs local `geode v0.6.7`.
- Committed branch commit `ebe1b7d` (unified paging loop `_read_execute_until_page`, empty-result handling, QUIC SNI fix).
- Restored WIP (uncommitted) in `client.py` (connect/HELLO retry loop `CONNECT_RETRY_ATTEMPTS`, `_cleanup_failed_connect`), `pool.py` (serial teardown + settle delay), `transport.py` (`HANDSHAKE_TIMEOUT = 30.0`), `conftest.py`/`test_concurrent.py` (min_size 2→1).
- Version drift: tag `v0.3.20`, code `__version__`/`setup.py` say `0.3.19`.

---

### Task 1: Finalize & commit the in-flight reliability WIP

**Files:**
- Modify (already in tree): `geode_client/client.py`, `pool.py`, `transport.py`, `tests/integration/conftest.py`, `tests/integration/test_concurrent.py`
- Add: `tests/unit/test_client.py` cases for the retry/cleanup path

- [ ] **Step 1:** Write failing unit tests for the new connect-retry behavior: transport error retried up to `CONNECT_RETRY_ATTEMPTS` then raises `GeodeConnectionError`; `AuthError` is NOT retried (raised immediately after cleanup); success on a later attempt returns connected. Mock the transport.
- [ ] **Step 2:** Run `pytest tests/unit/test_client.py -q -k retry` → expect some FAIL (asserting on behavior not yet covered) or PASS if WIP already implements it; adjust tests to pin exact behavior.
- [ ] **Step 3:** Ensure the WIP code satisfies the tests (it should — verify, tighten any gaps such as bounding total retry time).
- [ ] **Step 4:** `pytest tests/unit/ -q` → expect 736+ passed.
- [ ] **Step 5:** `ruff check geode_client/ && mypy geode_client/ --ignore-missing-imports` → clean.
- [ ] **Step 6:** Commit: `fix(client): add connect/HELLO retry, serial pool teardown, 30s HELLO timeout`

---

### Task 2: Typed error predicates + SQLSTATE constants

**Files:**
- Modify: `geode_client/errors.py` (add SQLSTATE constants + predicate helpers)
- Modify: `geode_client/__init__.py` (export new predicates/constants)
- Modify: `geode_client/client.py` (attach `.code` / `.sqlstate` to raised `QueryError` so predicates work)
- Test: `tests/unit/test_error.py`

Add (mirror Go `errors.go`):
```python
# SQLSTATE classes
STATUS_AUTH = "28000"; STATUS_SYNTAX = "42000"
STATUS_SERIALIZATION = "40001"; STATUS_DEADLOCK = "40502"
GEODE_AUTH_ALT = "08P01"; NO_DATA = "02000"
def is_auth_error(err) -> bool        # 28000 or 08P01
def is_syntax_error(err) -> bool      # 42000
def is_retryable_error(err) -> bool   # 40001 / 40P01 / 40502 / transport/timeout
```
`QueryError` must expose `.code` (the SQLSTATE parsed from the server error) — update where `QueryError(f"{code}: {message}")` is raised in `client.py` to also set `err.code = code`.

- [ ] **Step 1:** Write failing tests in `tests/unit/test_error.py`: `is_auth_error(QueryError(code="28000"))` true; `08P01` true; `is_syntax_error` for `42000`; `is_retryable_error` for `40001` and for `TransportError`; non-matching false.
- [ ] **Step 2:** `pytest tests/unit/test_error.py -q` → FAIL (predicates/`.code` absent).
- [ ] **Step 3:** Implement constants + predicates in `errors.py`; ensure `QueryError.__init__` accepts/stores `code`; update `client.py` raise sites to pass `code=`.
- [ ] **Step 4:** Export from `__init__.py`. `pytest tests/unit/ -q` → PASS, no regressions.
- [ ] **Step 5:** `ruff check && mypy` clean. Commit: `feat(errors): add SQLSTATE constants and is_auth_error/is_syntax_error/is_retryable_error predicates`

---

### Task 3: Version drift fix + bump

**Files:**
- Modify: `geode_client/__init__.py` (`__version__ = "0.3.21"`), `setup.py` (`version="0.3.21"`), `CHANGELOG.md`
- Test: `tests/unit/` (add a `test_version_consistency` asserting `__version__ == importlib.metadata`-ish or setup match)

- [ ] **Step 1:** Add a unit test asserting `__version__` matches the value in `setup.py` (parse setup.py or import). It should FAIL today (0.3.19 vs intended) only after bump — instead assert they are equal to each other (guards future drift).
- [ ] **Step 2:** Set both to `0.3.21`; update CHANGELOG.
- [ ] **Step 3:** `pytest tests/unit/ -q` → PASS. Commit: `chore(release): v0.3.21 and fix version single-source drift`

---

### Task 4: Validate + merge

- [ ] **Step 1:** Full local gate: `ruff check geode_client/ && mypy geode_client/ --ignore-missing-imports && pytest tests/unit/ -q && pytest tests/property/ -q`.
- [ ] **Step 2:** Integration gate vs local server: `GEODE_HOST=127.0.0.1 GEODE_PORT=3141 GEODE_USERNAME=geode GEODE_PASSWORD=... GEODE_SKIP_VERIFY=1 pytest tests/integration/ -m integration -q` → fix regressions via TDD.
- [ ] **Step 3:** Merge `codex/client-parity-sync` → `main`, push. **(Orchestrator handles push + tag + CI.)**

---

## Self-Review Notes
- Spec coverage: reliability WIP (T1), error predicates/SQLSTATE (T2 — the headline parity gap), version (T3), validate/merge (T4).
- `explain()`/`profile()` real plan parsing is a known stub but is **deferred** (Go exposes explain/profile only via its `graph` package; Zig has it; not part of the minimal cross-client baseline and risks scope creep). Note as future parity item.
- CDC/Backup/tenant_id remain Won't-Do per existing GAP_CLOSURE_REPORT (server-side features).

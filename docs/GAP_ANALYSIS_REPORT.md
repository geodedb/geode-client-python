# Gap Determination Report

**Date:** 2026-03-24
**Repository:** geode-client-python
**Branch:** main (commit 621c8ab)
**Analyst:** Claude Opus 4.6 (automated gap analysis)

---

## Summary

- **Total requirements analyzed:** 28
- **Implemented:** 0 | **Partial:** 7 | **Not Implemented:** 5 | **Unknown:** 0
- **Documentation/Quality issues:** 16
- **New gaps found:** 28
- **Previously open gaps resolved:** 0
- **Previously open gaps regressed:** 1 (SEC-019 savepoint validation)
- **Total open gaps:** 28

**Note:** The existing `docs/GAP_ANALYSIS.md` uses SEC-XXX IDs for security-specific findings. This report introduces GAP-XXXX IDs for a broader gap analysis covering functional, documentation, quality, and security dimensions.

---

## New Gaps

### Security Gaps

#### GAP-0001: GQL Injection in savepoint() and rollback_to() via f-string

- **Category:** Security
- **Severity:** Critical
- **Requirement source:** CLAUDE.md "Input Validation Pattern"; SEC-019 (previously marked CLOSED but fix not applied)
- **Current state (evidence):**
  - `geode_client/client.py:414` -- `await self.execute(f"SAVEPOINT {name}")` uses unsanitized f-string interpolation
  - `geode_client/client.py:419` -- `await self.execute(f"ROLLBACK TO SAVEPOINT {savepoint.name}")` same pattern
  - No call to `validate.identifier()` anywhere in `client.py` (confirmed by grep returning zero matches)
  - SEC-019 in `docs/GAP_ANALYSIS.md:311-323` claims "CLOSED" with `validate.identifier()` calls added, but the code does not contain them
- **Why this is a gap:** An attacker who controls the savepoint name can inject arbitrary GQL commands. The existing gap analysis falsely reports this as remediated.
- **Impact/Risk:** Arbitrary GQL execution via crafted savepoint names. This is a regression from the supposedly-closed SEC-019.
- **Recommended fix:** Add `validate.identifier(name)` at the top of `savepoint()` and `validate.identifier(savepoint.name)` at the top of `rollback_to()`. Add unit tests for injection attempts.
- **Acceptance criteria:**
  - `savepoint("x; DROP DATABASE")` raises `ValidationError`
  - `rollback_to(Savepoint(name="x; DROP"))` raises `ValidationError`
  - Unit tests cover alphanumeric-only enforcement

#### GAP-0002: gRPC Silent Fallback to insecure_channel When Cert Fetch Fails

- **Category:** Security
- **Severity:** High
- **Requirement source:** CLAUDE.md "TLS Errors" section; security.md "Authentication/authorization verified"
- **Current state (evidence):**
  - `geode_client/transport.py:641-642` -- When `skip_verify=True` and `_fetch_server_cert()` fails, code falls through to `grpc.aio.insecure_channel(target)` with no warning
  - No `SecurityWarning` or logging at this fallback point
- **Why this is a gap:** A user who requests `skip_verify=True` (accept any cert) may silently get a completely unencrypted connection if the cert probe fails. This is a security downgrade beyond what the user requested.
- **Impact/Risk:** Credentials and query data transmitted in plaintext without the user's knowledge.
- **Recommended fix:** Log a `SecurityWarning` at the fallback point. Consider raising an error instead of silently downgrading, or at minimum emit `warnings.warn("Falling back to insecure (plaintext) gRPC channel", SecurityWarning)`.
- **Acceptance criteria:**
  - A `SecurityWarning` is emitted when the fallback occurs
  - Unit test verifies the warning is raised

#### GAP-0003: No Max Message Size Validation in _read_message()

- **Category:** Security
- **Severity:** Medium
- **Requirement source:** SEC-026 pattern (buffer limits); security.md "Input validation"
- **Current state (evidence):**
  - `geode_client/transport.py:438` -- `msg_len = struct.unpack(">I", self._buffer[:4])[0]` reads a 4-byte length prefix with no upper bound check
  - Maximum possible value is 2^32 - 1 = ~4GB
  - No `MAX_MESSAGE_SIZE` constant or check before allocating
- **Why this is a gap:** A malicious or buggy server can send a crafted length prefix causing the client to allocate up to 4GB of memory, enabling a denial-of-service attack.
- **Impact/Risk:** Client-side OOM/DoS from a single malicious message.
- **Recommended fix:** Add a `MAX_MESSAGE_SIZE` constant (e.g., 64MB) and validate `msg_len` immediately after unpacking. Raise `TransportError` if exceeded.
- **Acceptance criteria:**
  - `msg_len` is checked against a constant before reading the body
  - Unit test with oversized length prefix raises `TransportError`

#### GAP-0004: TransportConfig __repr__ Exposes Password in Logs/Tracebacks

- **Category:** Security
- **Severity:** Medium
- **Requirement source:** security.md "Error messages don't leak sensitive data"
- **Current state (evidence):**
  - `geode_client/transport.py:70-83` -- `TransportConfig` is a `@dataclass` with `password: str = ""` field
  - No custom `__repr__` method defined (grep for `__repr__` in transport.py returns zero matches)
  - Default dataclass `__repr__` includes all fields including `password`
- **Why this is a gap:** Any logging, traceback, or debug output that prints a `TransportConfig` instance will expose the password in plaintext.
- **Impact/Risk:** Password exposure in logs, error reports, and debugging sessions.
- **Recommended fix:** Add a custom `__repr__` that masks the password field (e.g., `password='***'` when non-empty).
- **Acceptance criteria:**
  - `repr(TransportConfig(host="h", port=1, password="secret"))` does not contain "secret"
  - Unit test verifies masking

#### GAP-0005: No SecurityWarning Emitted at Connection.connect() Time

- **Category:** Security
- **Severity:** Medium
- **Requirement source:** SEC-005 (TLS Verification Bypass, marked CLOSED)
- **Current state (evidence):**
  - `geode_client/client.py:51-54` -- `SecurityWarning` class is defined
  - Grep for `warnings.warn.*SecurityWarning` across `geode_client/` returns zero matches
  - SEC-005 in GAP_ANALYSIS.md claims "Warning emitted when skip_verify=True" but no `warnings.warn()` call exists in the codebase
- **Why this is a gap:** SEC-005 was marked CLOSED but the actual warning emission code was never added. Users get no runtime warning when using `skip_verify=True`.
- **Impact/Risk:** Users unknowingly run with disabled TLS verification in production. This is a regression from the supposedly-closed SEC-005.
- **Recommended fix:** Add `warnings.warn("TLS verification disabled...", SecurityWarning, stacklevel=2)` in `Connection.connect()` when `skip_verify=True`.
- **Acceptance criteria:**
  - `pytest.warns(SecurityWarning)` test passes when connecting with `skip_verify=True`

#### GAP-0006: Transitive Dependency Vulnerabilities (6 CVEs in 5 packages)

- **Category:** Security
- **Severity:** High
- **Requirement source:** security.md "Rotate any secrets that may have been exposed"; setup.py dependency management
- **Current state (evidence):**
  - `pip-audit` output shows 6 known vulnerabilities:
    - `black 26.1.0` -- CVE-2026-32274 (fix: 26.3.1)
    - `cryptography 46.0.4` -- CVE-2026-26007 (fix: 46.0.5)
    - `pip 25.3` -- CVE-2026-1703 (fix: 26.0)
    - `pyasn1 0.6.2` -- CVE-2026-30922 (fix: 0.6.3)
    - `pyopenssl 25.3.0` -- CVE-2026-27448 (fix: 26.0.0)
    - `pyopenssl 25.3.0` -- CVE-2026-27459 (fix: 26.0.0)
  - `cryptography` and `pyopenssl` are transitive runtime dependencies (via aioquic)
- **Why this is a gap:** Known CVEs in runtime dependency chain. `cryptography` is used for TLS operations.
- **Impact/Risk:** Potential exploitation of known vulnerabilities in cryptographic libraries.
- **Recommended fix:** Update `cryptography>=46.0.5`, `pyasn1>=0.6.3`, `pyopenssl>=26.0.0` in constraints. Update `black>=26.3.1` and `pip>=26.0` in dev environment.
- **Acceptance criteria:**
  - `pip-audit` reports zero vulnerabilities
  - CI passes after upgrade

### Functional Gaps

#### GAP-0007: CDC Diagnostics/Control Proto Messages With No Client API

- **Category:** Feature
- **Severity:** Low
- **Requirement source:** `proto/geode.proto:14-15` (rpc definitions), `proto/geode.proto:482-536` (message definitions)
- **Current state (evidence):**
  - Proto defines `GetCdcDiagnostics` and `ControlCdc` RPCs with request/response messages
  - Generated stubs exist in `geode_client/proto/geode_pb2_grpc.py:77-86`
  - No client-facing API wraps these RPCs in `client.py` or any other module
- **Why this is a gap:** Wire protocol supports CDC operations but the Python client provides no way to invoke them.
- **Impact/Risk:** Users cannot manage CDC from Python. Low severity as CDC is an administrative feature.
- **Recommended fix:** Add `CdcClient` or methods on `Connection` to wrap CDC RPCs. Alternatively, document as "not yet supported."
- **Acceptance criteria:**
  - Either a client API exists for CDC operations, or explicit documentation states the feature is planned

#### GAP-0008: Backup/Restore Proto Messages With No Client API

- **Category:** Feature
- **Severity:** Low
- **Requirement source:** `proto/geode.proto:49-51` (message fields), `proto/geode.proto:545-569` (message definitions)
- **Current state (evidence):**
  - Proto defines `BackupRequest`, `RestoreRequest`, `UploadBackupRequest` messages
  - Generated stubs exist in proto package
  - No client-facing API wraps these messages
- **Why this is a gap:** Wire protocol supports backup/restore but the Python client provides no way to invoke them.
- **Impact/Risk:** Users cannot trigger backup/restore from Python. Low severity as backup is an administrative feature.
- **Recommended fix:** Add backup/restore methods or document as "not yet supported."
- **Acceptance criteria:**
  - Either a client API exists, or documentation explicitly states planned status

#### GAP-0009: create_pool() Not Exported in __init__.py

- **Category:** Feature
- **Severity:** Low
- **Requirement source:** `geode_client/pool.py:228` defines `async def create_pool()`
- **Current state (evidence):**
  - `geode_client/pool.py:228` -- `async def create_pool(` is defined as a public convenience function
  - `geode_client/__init__.py:49` -- only `ConnectionPool` is imported from pool; `create_pool` is absent
  - `geode_client/__init__.py:75-129` -- `__all__` list does not include `create_pool`
- **Why this is a gap:** Public function defined but not accessible via the package's public API.
- **Impact/Risk:** Users must import directly from `geode_client.pool` instead of `geode_client`.
- **Recommended fix:** Add `create_pool` to `__init__.py` imports and `__all__`.
- **Acceptance criteria:**
  - `from geode_client import create_pool` works

#### GAP-0010: tenant_id Proto Field Not Exposed in Client

- **Category:** Feature
- **Severity:** Low
- **Requirement source:** `proto/geode.proto:80` -- `optional string tenant_id = 3` in HelloRequest
- **Current state (evidence):**
  - `proto/geode.proto:80` defines `tenant_id` on `HelloRequest`
  - Generated Python code has the field (`geode_client/proto/geode_pb2.pyi:212`)
  - No reference to `tenant_id` in `geode_client/client.py` or `geode_client/transport.py` (outside proto)
- **Why this is a gap:** Multi-tenancy support exists in the wire protocol but the client has no way to set it.
- **Impact/Risk:** Multi-tenant deployments cannot be addressed from the Python client.
- **Recommended fix:** Add `tenant_id` parameter to `Client`, `TransportConfig`, and pass it in the `HelloRequest`.
- **Acceptance criteria:**
  - `Client(host="h", port=1, tenant_id="t1")` sends `tenant_id` in HelloRequest

### Documentation Gaps

#### GAP-0011: Version Mismatch Between __init__.py and setup.py

- **Category:** Docs
- **Severity:** Medium
- **Requirement source:** Package versioning consistency
- **Current state (evidence):**
  - `geode_client/__init__.py:131` -- `__version__ = "0.3.18"`
  - `setup.py:16` -- `version="0.3.19"`
- **Why this is a gap:** `geode_client.__version__` reports a different version than what pip installs. This breaks version-checking code and confuses users.
- **Impact/Risk:** Users and tooling get inconsistent version information.
- **Recommended fix:** Synchronize both to the same version. Consider using a single source of truth (e.g., read from `__init__.py` in `setup.py`).
- **Acceptance criteria:**
  - `geode_client.__version__` matches `setup.py` version

#### GAP-0012: CLAUDE.md States 537 Unit Tests, Actual Count is 636

- **Category:** Docs
- **Severity:** Low
- **Requirement source:** `CLAUDE.md` "Test Commands" section
- **Current state (evidence):**
  - CLAUDE.md states "Run all unit tests (537 tests)"
  - `pytest tests/unit/ --co -q` reports "636 tests collected"
- **Why this is a gap:** Documentation is stale, understating test coverage by 99 tests.
- **Impact/Risk:** Developers may question test suite completeness based on outdated docs.
- **Recommended fix:** Update CLAUDE.md to reflect current test count (636).
- **Acceptance criteria:**
  - CLAUDE.md test count matches actual `pytest --co` output

#### GAP-0013: CLAUDE.md States 23 Types, Actual Count is 26

- **Category:** Docs
- **Severity:** Low
- **Requirement source:** `CLAUDE.md` "geode_client/types.py" section
- **Current state (evidence):**
  - CLAUDE.md says "ValueKind: Enum of 23 supported types"
  - `geode_client/types.py:12-40` shows 26 enum members (NODE, EDGE, PATH were added)
- **Why this is a gap:** Documentation understates type system capabilities.
- **Recommended fix:** Update CLAUDE.md to say "26 supported types" and list NODE, EDGE, PATH.
- **Acceptance criteria:**
  - CLAUDE.md type count matches `ValueKind` enum member count

#### GAP-0014: CLAUDE.md Missing test_prepared_statement.py in Project Structure

- **Category:** Docs
- **Severity:** Low
- **Requirement source:** `CLAUDE.md` "Project Structure" section
- **Current state (evidence):**
  - `tests/unit/test_prepared_statement.py` exists on disk
  - CLAUDE.md project structure tree does not list this file
- **Why this is a gap:** New test file not reflected in documentation.
- **Recommended fix:** Add `test_prepared_statement.py` to the project structure in CLAUDE.md.
- **Acceptance criteria:**
  - File appears in CLAUDE.md project structure

#### GAP-0015: CLAUDE.md Missing Multiple Public Symbols

- **Category:** Docs
- **Severity:** Low
- **Requirement source:** `CLAUDE.md` module documentation sections
- **Current state (evidence):**
  - `geode_client/__init__.py:33-47` exports: `BatchResult`, `PreparedStatement`, `QueryPlan`, `QueryProfile`, `PlanOperation`, `SecurityWarning`, `open_database`
  - CLAUDE.md "geode_client/client.py" section does not mention `PreparedStatement`, `BatchResult`, `QueryPlan`, `QueryProfile`, `PlanOperation`, `open_database`
  - `SecurityWarning` is listed in error classes but not in the main client.py documentation
- **Why this is a gap:** Public API symbols are undocumented.
- **Recommended fix:** Add all missing symbols to the relevant CLAUDE.md module documentation sections.
- **Acceptance criteria:**
  - Every symbol in `__all__` has a corresponding entry in CLAUDE.md

#### GAP-0016: README Port Inconsistency (8443 vs 3141)

- **Category:** Docs
- **Severity:** Medium
- **Requirement source:** `CLAUDE.md` "Wire Protocol Reference" (port 3141); README.md examples
- **Current state (evidence):**
  - `README.md:52` -- `client = Client(host="127.0.0.1", port=8443, skip_verify=True)`
  - `README.md:176` -- `port=8443`
  - `README.md:344` -- `quic://geode.example.com:8443`
  - `README.md:404` -- `port=8443`
  - CLAUDE.md and transport.py use port 3141 as the QUIC default
- **Why this is a gap:** README examples use a non-standard port that will not work with default Geode server configuration.
- **Impact/Risk:** Users copying README examples will get connection failures.
- **Recommended fix:** Change all README port references from 8443 to 3141.
- **Acceptance criteria:**
  - No occurrence of port 8443 in README.md

#### GAP-0017: CHANGELOG.md Empty Despite Being at v0.3.19

- **Category:** Docs
- **Severity:** Medium
- **Requirement source:** `CHANGELOG.md` header references Keep a Changelog format
- **Current state (evidence):**
  - `CHANGELOG.md` contains only the header template with an empty `[Unreleased]` section
  - Project is at version 0.3.19 with extensive commit history
- **Why this is a gap:** No release history is documented. Users cannot determine what changed between versions.
- **Impact/Risk:** Users upgrading have no way to assess breaking changes or new features.
- **Recommended fix:** Backfill changelog entries for at least the current release, or generate from git history.
- **Acceptance criteria:**
  - CHANGELOG.md contains entries for at least the current version

#### GAP-0018: CLAUDE.md States protobuf>=4.21.0, setup.py Has >=6.31.0

- **Category:** Docs
- **Severity:** Low
- **Requirement source:** `CLAUDE.md` "Dependencies" section
- **Current state (evidence):**
  - CLAUDE.md says `protobuf>=4.21.0`
  - `setup.py:50` says `protobuf>=6.31.0`
- **Why this is a gap:** Documentation version does not match actual requirement. Users following CLAUDE.md may install an incompatible protobuf version.
- **Recommended fix:** Update CLAUDE.md to show `protobuf>=6.31.0`.
- **Acceptance criteria:**
  - CLAUDE.md dependency versions match setup.py

#### GAP-0019: Pool max_size Default Mismatch Between README and Code

- **Category:** Docs
- **Severity:** Low
- **Requirement source:** `README.md:396`; `geode_client/pool.py:38`
- **Current state (evidence):**
  - `README.md:396` -- documents `max_size` default as `10`
  - `geode_client/pool.py:38` -- `max_size: int = 3`
  - `geode_client/pool.py:232` -- `create_pool()` also defaults to `max_size=3`
- **Why this is a gap:** README misleads users about default pool behavior.
- **Recommended fix:** Update README to show default `max_size=3`, or change code default to 10 if 10 is the intended value.
- **Acceptance criteria:**
  - README and code agree on the default value

### Code Quality / CI Gaps

#### GAP-0020: Coverage 74% vs 80% Guideline (CI Threshold Only 70%)

- **Category:** Test
- **Severity:** Medium
- **Requirement source:** `CLAUDE.md` "Unit Tests - Target 80%+ coverage"; testing.md "Minimum Test Coverage: 80%"
- **Current state (evidence):**
  - `pytest --cov` reports `TOTAL 1837 472 74%`
  - `.gitlab-ci.yml:40` -- `coverage_threshold: "70"` with comment "Lower threshold: transport code requires live server"
- **Why this is a gap:** Coverage is 6 percentage points below the documented 80% target. CI threshold set even lower at 70%.
- **Impact/Risk:** Untested code paths in production modules.
- **Recommended fix:** Increase coverage by adding mock-based tests for transport and client connection paths. Raise CI threshold toward 80%.
- **Acceptance criteria:**
  - Coverage >= 80% in `pytest --cov` output
  - CI `coverage_threshold` set to at least "80"

#### GAP-0021: transport.py Coverage at 36%

- **Category:** Test
- **Severity:** High
- **Requirement source:** testing.md "Minimum Test Coverage: 80%"
- **Current state (evidence):**
  - `pytest --cov` shows `geode_client/transport.py 449 288 36%`
  - Most of `connect()`, `_read_message()`, `send_*()`, and `_fetch_server_cert()` are untested
- **Why this is a gap:** The transport layer is the most security-critical module (TLS, message parsing, connection management) and has the lowest coverage.
- **Impact/Risk:** Bugs in TLS handling, message parsing, or connection logic could go undetected.
- **Recommended fix:** Add mock-based unit tests for QUIC and gRPC transport connect/send/receive paths.
- **Acceptance criteria:**
  - `transport.py` coverage >= 70% (interim target given live-server dependency)

#### GAP-0022: client.py Coverage at 61%

- **Category:** Test
- **Severity:** Medium
- **Requirement source:** testing.md "Minimum Test Coverage: 80%"
- **Current state (evidence):**
  - `pytest --cov` shows `geode_client/client.py 395 156 61%`
  - Uncovered: connection lifecycle (lines 327-386), transaction commit/rollback, query execution
- **Why this is a gap:** Core client functionality including transactions and queries is not covered by unit tests.
- **Impact/Risk:** Regressions in connection, transaction, or query handling may not be caught.
- **Recommended fix:** Add mock-based tests for `Connection.connect()`, `query()`, `execute()`, `begin()`/`commit()`/`rollback()`.
- **Acceptance criteria:**
  - `client.py` coverage >= 80%

#### GAP-0023: Lint Regressions in transport.py

- **Category:** Code Quality
- **Severity:** Low
- **Requirement source:** CLAUDE.md "Linting Commands"
- **Current state (evidence):**
  - `ruff check geode_client/` reports E401 and I001 at `transport.py:588` (`import tempfile, os`)
  - `ruff format --check geode_client/` reports `transport.py` would be reformatted
- **Why this is a gap:** Recent commits introduced lint violations that were not caught.
- **Impact/Risk:** CI lint stage may fail; inconsistent code style.
- **Recommended fix:** Split the import (`import os` + `import tempfile`) and run `ruff format geode_client/transport.py`.
- **Acceptance criteria:**
  - `ruff check geode_client/` passes with zero errors
  - `ruff format --check geode_client/` passes

#### GAP-0024: mypy Type Error in transport.py _fetch_server_cert Return Type

- **Category:** Code Quality
- **Severity:** Low
- **Requirement source:** CLAUDE.md "Linting Commands" (mypy)
- **Current state (evidence):**
  - `geode_client/transport.py:561` -- `def _fetch_server_cert(self, host: str, port: int) -> bytes:` declares return type `bytes`
  - `geode_client/transport.py:600` -- `return pem, cn` actually returns `tuple[bytes, Optional[Any]]`
  - `mypy geode_client/` reports: `error: Incompatible return value type (got "tuple[bytes, Optional[Any]]", expected "bytes") [return-value]`
- **Why this is a gap:** Type annotation does not match implementation. Function signature was updated to return CN but annotation was not.
- **Impact/Risk:** Callers relying on type hints get incorrect information. mypy CI job will fail.
- **Recommended fix:** Update return type to `tuple[bytes, Optional[str]]`.
- **Acceptance criteria:**
  - `mypy geode_client/` reports zero errors (1 error currently)

#### GAP-0025: black Still in Dev Dependencies Despite ruff Replacement

- **Category:** Code Quality
- **Severity:** Low
- **Requirement source:** CLAUDE.md "Linting Commands" (ruff preferred)
- **Current state (evidence):**
  - `setup.py:60` -- `"black>=23.0.0"` listed in dev dependencies
  - `.gitlab-ci.yml:20` -- `run_black: true` in lint component configuration
  - CLAUDE.md says "black>=23.0.0 - Formatting (legacy, ruff preferred)"
  - `black 26.1.0` has CVE-2026-32274
- **Why this is a gap:** Redundant formatter adds CI time, dependency surface, and currently has a known vulnerability.
- **Impact/Risk:** Unnecessary dependency with active CVE. Potential formatting conflicts between black and ruff.
- **Recommended fix:** Remove `black` from `setup.py` dev deps. Set `run_black: false` in CI. Remove from pre-commit if present.
- **Acceptance criteria:**
  - `black` not in `setup.py`
  - `run_black: false` or removed from CI config

#### GAP-0026: mypy ignore_errors=True on auth.py Module

- **Category:** Code Quality
- **Severity:** Medium
- **Requirement source:** CLAUDE.md "Linting Commands" (mypy); coding-style.md quality checklist
- **Current state (evidence):**
  - `mypy.ini:36-39` -- `[mypy-geode_client.auth]` section has `ignore_errors = True` with comment "needs to be updated for protobuf transport"
  - `geode_client/auth.py` has 99% test coverage (281 stmts, 1 miss)
  - The module appears fully migrated to protobuf transport
- **Why this is a gap:** Type checking is completely bypassed for auth.py. The comment suggests this was temporary but was never reverted.
- **Impact/Risk:** Type errors in authentication code (security-critical) go undetected.
- **Recommended fix:** Remove `ignore_errors = True` from `[mypy-geode_client.auth]` and fix any resulting type errors.
- **Acceptance criteria:**
  - `mypy.ini` does not ignore errors for `geode_client.auth`
  - `mypy geode_client/auth.py` passes

#### GAP-0027: Integration Tests Still allow_failure:true (SEC-015 Blocked)

- **Category:** CI-CD
- **Severity:** Low
- **Requirement source:** SEC-015 in `docs/GAP_ANALYSIS.md:237-253`
- **Current state (evidence):**
  - `.gitlab-ci.yml:211` -- `allow_failure: true  # Allow failure until Geode server image is published`
  - SEC-015 status: BLOCKED, waiting for Docker image
- **Why this is a gap:** Integration test failures do not block merges. Already tracked as SEC-015 but still unresolved.
- **Impact/Risk:** Code with failing integration tests can be merged.
- **Recommended fix:** Publish Geode server Docker image and remove `allow_failure: true`.
- **Acceptance criteria:**
  - `allow_failure` removed from integration test job
  - Integration tests run against published Geode server image

#### GAP-0028: SBOM Jobs Still allow_failure:true

- **Category:** CI-CD
- **Severity:** Low
- **Requirement source:** SEC-016 (marked CLOSED in GAP_ANALYSIS.md)
- **Current state (evidence):**
  - `.gitlab-ci.yml:118` -- `sbom-generate:` has `allow_failure: true`
  - `.gitlab-ci.yml:121` -- `sbom-scan:` has `allow_failure: true`
  - SEC-016 in GAP_ANALYSIS.md claims "CLOSED - Removed allow_failure from SBOM scanning" but the flags remain
- **Why this is a gap:** SBOM scanning failures do not block merges, despite SEC-016 claiming this was fixed. This is a regression or false closure.
- **Impact/Risk:** Supply chain issues may not be caught before merge.
- **Recommended fix:** Remove `allow_failure: true` from both SBOM jobs.
- **Acceptance criteria:**
  - Neither `sbom-generate` nor `sbom-scan` has `allow_failure: true`

---

## Updated Gaps (evidence changed)

| Gap-ID | Change | Updated Evidence |
|--------|--------|-----------------|
| (none) | -- | -- |

## Resolved Gaps (ready to close)

| Gap-ID | Resolution Evidence |
|--------|-------------------|
| (none -- all gaps are new) | -- |

## Regressions from Previously Closed Findings

| Finding | Claimed Status | Actual Status | New Gap-ID |
|---------|---------------|---------------|------------|
| SEC-019 (Savepoint validation) | CLOSED | Fix not applied in code | GAP-0001 |
| SEC-005 (SecurityWarning emission) | CLOSED | No `warnings.warn()` call exists | GAP-0005 |
| SEC-016 (SBOM allow_failure) | CLOSED | `allow_failure: true` still present | GAP-0028 |

---

## Gap Priority Matrix

| Severity | Count | Gap-IDs |
|----------|-------|---------|
| Critical | 1 | GAP-0001 |
| High | 3 | GAP-0002, GAP-0006, GAP-0021 |
| Medium | 8 | GAP-0003, GAP-0004, GAP-0005, GAP-0011, GAP-0016, GAP-0017, GAP-0020, GAP-0026 |
| Low | 16 | GAP-0007, GAP-0008, GAP-0009, GAP-0010, GAP-0012, GAP-0013, GAP-0014, GAP-0015, GAP-0018, GAP-0019, GAP-0022, GAP-0023, GAP-0024, GAP-0025, GAP-0027, GAP-0028 |

## Recommended Priority Order

1. **GAP-0001** (Critical) -- GQL injection in savepoint/rollback_to: immediate fix required
2. **GAP-0002** (High) -- Silent insecure gRPC fallback: security warning needed
3. **GAP-0005** (Medium) -- SecurityWarning not emitted: regression from SEC-005
4. **GAP-0006** (High) -- Transitive dependency CVEs: update dependencies
5. **GAP-0021** (High) -- transport.py 36% coverage: test the most critical module
6. **GAP-0003** (Medium) -- Message size validation: DoS protection
7. **GAP-0004** (Medium) -- Password in repr: log safety
8. **GAP-0026** (Medium) -- mypy disabled for auth.py: type safety in security code
9. **GAP-0011** (Medium) -- Version mismatch: user confusion
10. **GAP-0023/0024** (Low) -- Lint/mypy fixes: quick wins

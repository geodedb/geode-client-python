# Gap Closure Report

**Date:** 2026-03-24
**Repository:** geode-client-python
**Branch:** main
**Baseline:** commit 621c8ab (pre-audit)

---

## Summary

| Status | Count |
|--------|-------|
| Closed | 18 |
| Won't Do | 6 |
| Blocked | 1 |
| Deferred | 3 |
| **Total** | **28** |

---

## Closed Gaps (18)

| Gap-ID | Title | Commit | Severity |
|--------|-------|--------|----------|
| GAP-0001 | GQL injection in savepoint/rollback_to | `8838ce9` | Critical |
| GAP-0002 | Silent insecure gRPC fallback | `1f66796` | High |
| GAP-0003 | No MAX_MESSAGE_SIZE check | `94b4acb` | Medium |
| GAP-0004 | TransportConfig repr exposes password | `94b4acb` | Medium |
| GAP-0005 | SecurityWarning not emitted at connect (SEC-005 regression) | `1f66796` | Medium |
| GAP-0009 | create_pool() not exported | `af98cbd` | Low |
| GAP-0011 | Version mismatch __init__.py vs setup.py | `dba04e1` | Medium |
| GAP-0012 | CLAUDE.md stale test count (537->642) | `90debdb` | Low |
| GAP-0013 | CLAUDE.md stale type count (23->26) | `90debdb` | Low |
| GAP-0014 | CLAUDE.md missing test_prepared_statement.py | `90debdb` | Low |
| GAP-0015 | CLAUDE.md missing public symbols | `90debdb` | Low |
| GAP-0016 | README port inconsistency (8443->3141) | `af98cbd` | Medium |
| GAP-0018 | CLAUDE.md protobuf version stale | `90debdb` | Low |
| GAP-0019 | Pool max_size default mismatch in docs | `af98cbd` | Low |
| GAP-0023 | Ruff lint regressions (E401, I001) | `fbd134a` | Low |
| GAP-0024 | mypy type error: _fetch_server_cert return type | `fbd134a` | Low |
| GAP-0025 | black still in dev deps and CI | `dba04e1` | Low |
| GAP-0028 | SBOM allow_failure:true (SEC-016 regression) | `af98cbd` | Low |

## Won't Do (6)

| Gap-ID | Title | Reason |
|--------|-------|--------|
| GAP-0007 | CDC diagnostics proto not exposed | Server-side admin feature, not client scope |
| GAP-0008 | Backup/restore proto not exposed | Server-side admin feature, separate effort |
| GAP-0010 | tenant_id proto field not exposed | Multi-tenancy not yet supported by server |
| SEC-022 | CI component pinning (@latest/@main) | Managed by organizational CI catalog control |
| -- | Pool max_size default change to 10 | Breaking change; doc fix (GAP-0019) applied instead |
| -- | Full auth module rewrite | Separate effort; recommend quarantine from exports |

## Blocked (1)

| Gap-ID | Title | Blocker |
|--------|-------|---------|
| GAP-0027 / SEC-015 | Integration tests allow_failure:true | Geode server Docker image not published to container registry |

## Deferred (3)

| Gap-ID | Title | Reason |
|--------|-------|--------|
| GAP-0006 | Transitive dependency CVEs | Requires aioquic compatibility testing; recommend separate PR |
| GAP-0017 | CHANGELOG.md empty | Requires git log analysis for historical entries |
| GAP-0020/0021/0022 | Coverage below 80% | Requires significant test additions; recommend separate effort |
| GAP-0026 | mypy ignore_errors on auth.py | Auth module needs rewrite first |

---

## Verification

| Check | Result |
|-------|--------|
| `ruff check geode_client/` | All checks passed |
| `ruff format --check geode_client/` | 9 files already formatted |
| `mypy geode_client/ --ignore-missing-imports` | Success: no issues found in 11 source files |
| `pytest tests/unit/ -q` | 642 passed, 10 warnings |
| Clean working tree | All changes committed |

## Commits (7)

1. `8838ce9` - fix: close GAP-0001 - prevent GQL injection in savepoint/rollback_to
2. `fbd134a` - fix: close GAP-0023/0024 - fix lint, mypy, and format regressions
3. `1f66796` - fix: close GAP-0002/GAP-0005 - add security warnings for skip_verify
4. `94b4acb` - fix: close GAP-0003/GAP-0004 - add MAX_MESSAGE_SIZE and redact password
5. `dba04e1` - fix: close GAP-0011/GAP-0025 - sync version and remove black
6. `af98cbd` - fix: close GAP-0009/0016/0019/0028 - exports, README, CI fixes
7. `90debdb` - docs: close GAP-0012 through GAP-0018 - update CLAUDE.md

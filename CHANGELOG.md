# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.1] - 2026-11-17

### Fixed
- SONNY-6723: the declared dependency floors could not import the client.
  `setup.py` declared `grpcio>=1.50.0`, but the committed `geode_pb2_grpc.py`
  raises `RuntimeError` at import below its `GRPC_GENERATED_VERSION` (1.73.1),
  and `import geode_client` loads that stub eagerly. The other floors were also
  unsatisfiable or too old: `aioquic>=0.9.0` lacks `StopSendingReceived` (added
  in 0.9.22) and has no wheel for current Pythons, `pyOpenSSL>=26.0.0` requires
  `cryptography>=46`, contradicting `cryptography>=44.0.0`, and `requirements.txt`
  declared different floors from `setup.py`. Runtime floors are now identical
  in `setup.py` and `requirements.txt`: `aioquic>=0.9.22`, `protobuf>=6.33.5`
  (gencode needs >=6.31.0; 6.33.5 fixes CVE-2025-4565 and CVE-2026-0994;
  protobuf 7.x is supported), `grpcio>=1.73.1`, `pyOpenSSL>=26.4.0`, and
  `cryptography>=50.0.0` (fixes CVE-2026-69247/69248/69249). The `dev` extra's
  `grpcio-tools` floor is now 1.73.1, the generator of the committed stubs.

### Added
- `scripts/check_min_deps.py` and the `test:min-deps` CI job install the
  package into a clean venv with every runtime dependency at its declared floor
  and prove `import geode_client` works; `tests/unit/test_dependency_floors.py`
  checks the floors against the stubs' version guards and against
  `requirements.txt`.

## [0.5.0] - 2026-08-25

### Added
- Configurable QUIC timeouts (ENG-3914): `read_timeout` (per-message read,
  default 30s) and `idle_timeout` (QUIC connection idle cap, default 60s) are
  now fields on `TransportConfig`, keyword arguments on `Connection`/`Client`,
  DSN query parameters (`?read_timeout=…&idle_timeout=…`, seconds) emitted by
  `format_dsn` when non-default, and are threaded through `Client.from_url` and
  `create_pool_from_dsn`. Defaults preserve the previous behaviour.

### Fixed
- ENG-3914: long-running server work no longer kills QUIC connections.
  `QuicTransport._read_message` hardcoded a 30s read timeout (so every
  execute/pull/ping/transaction call failed with "Timeout reading message
  length" after 30s) and `QuicConfiguration` was built without `idle_timeout`,
  letting aioquic's 60s default close the connection ("Stream closed") even
  when the read timeout was raised. The streaming pager's hardcoded 5s
  `wait_for` around `read_next()` now uses the configured read timeout.
- ENG-3909: `Connection._proto_value_to_python` had no `decimal_val` arm, so
  every FLOAT-typed engine result (float literals, arithmetic, `sqrt()`,
  `vector_cosine()`, `CAST(... AS DECIMAL)`) decoded as NULL and embeddings
  came back as `[None, None, …]`. The new arm prefers the engine's `orig_repr`
  and otherwise scales the exact i128 coefficient, so no rounding or float
  round-trip occurs. An unhandled oneof arm now raises `GeodeError` naming the
  arm instead of silently fabricating NULL. `types._DECODERS` gained the float
  family (FLOAT/DOUBLE/REAL/NUMERIC) and `Value.as_object` also serves
  NODE/EDGE/PATH so nested FLOAT properties are reachable.
- ENG-3910: `Connection._python_to_proto_value` had no container arm, so list
  parameters were sent as `string_val` holding the Python repr and predicates
  such as `WHERE NOT d.source IN $blocked` failed open. Lists/tuples now encode
  as `list_val` and dicts as `map_val`, recursing per element with a depth
  guard of 64 (mirroring the server/CLI `PARAM_MAX_DEPTH`); `bytes` and
  `Decimal` get explicit `bytes_val`/`decimal_val` arms.

## [0.4.1] - 2026-06-19

### Fixed
- Version-consistency test pinned the pre-0.4.0 version; package,
  `setup.py`, and the guard test are back in lockstep.

## [0.4.0] - 2026-06-19

### Added
- Multi-tenancy + FLE support on the HELLO handshake (GAP-0841): `Connection`
  and `Client.from_url` now accept `tenant` (sent as `HelloRequest.tenant_id`)
  and `role` (sent as `HelloRequest.role`). Both are also parsable from the DSN
  query string (`?tenant=…&role=…`, with `tenant_id` accepted as an alias) and
  are only sent when non-empty. The vendored `proto/geode.proto` was resynced to
  add `HelloRequest.role = 8` and the generated `_pb2`/`_pb2.pyi` regenerated.

## [0.3.21] - 2026-06-01

### Added
- Typed error classification mirroring the Go and Node.js clients:
  `is_auth_error`, `is_syntax_error`, and `is_retryable_error` predicates plus
  ISO/IEC 39075 (GQL) SQLSTATE status-class constants (`STATUS_AUTH`,
  `STATUS_SYNTAX`, `STATUS_SERIALIZATION`, `STATUS_DEADLOCK`,
  `STATUS_DEADLOCK_DETECTED`, `GEODE_AUTH_ALT`, `NO_DATA`).
- `QueryError.code` exposes the SQLSTATE status class parsed from the server
  error response (`None` when unknown); `AuthError.code` defaults to `28000`.

### Fixed
- Connection establishment now retries transport/HELLO failures up to three
  attempts (auth failures are not retried) with partial-transport cleanup
  between attempts.
- Connection pool teardown closes pooled connections serially with a brief
  settle delay to avoid intermittent HELLO timeouts in concurrent workloads.
- HELLO handshake read timeout raised to 30s for slow/cold-start servers.
- Single-source the package version; `__version__` and `setup.py` are now kept
  in lockstep and guarded by a unit test.

## [0.3.19] - 2026-03-24

### Fixed
- Close remaining gap analysis items (GAP-0006, GAP-0017, GAP-0020/21/22, GAP-0026)
- Update gap analysis tracking with closure report
- Update CLAUDE.md stale documentation (GAP-0012 through GAP-0018)
- Fix exports, README, and CI configuration (GAP-0009/0016/0019/0028)
- Sync version and remove black dependency (GAP-0011/GAP-0025)
- Add MAX_MESSAGE_SIZE check and redact password in repr (GAP-0003/GAP-0004)
- Add security warnings for skip_verify (GAP-0002/GAP-0005)
- Fix lint, mypy, and format regressions in transport.py (GAP-0023/0024)
- Prevent GQL injection in savepoint/rollback_to (GAP-0001)

## [0.3.18] - 2025-12-15

### Fixed
- Add `read_next()` to GrpcTransport for multi-message streaming
- Prefer cert CN over config server_name for skip_verify override
- Extract cert CN for gRPC ssl_target_name_override
- Restore cert fetch flow for skip_verify gRPC TLS
- Add ALPN h2 to cert probe for gRPC TLS compatibility
- Use insecure channel for skip_verify gRPC instead of cert probe
- Always set SNI server_name and use config host for gRPC TLS override

## [0.3.17] - 2025-11-20

### Fixed
- Check for docs/Makefile before running sphinx build in CI
- Allow SBOM jobs to fail on DNS/network issues
- Add timeout to QUIC message read to prevent indefinite hangs
- Add complex type deserialization and fix pool defaults

## [0.3.14] - 2025-10-15

### Fixed
- Bump version and add --disable-auth to CI
- Switch Docker image refs from GitLab registry to Docker Hub
- Use geodedb/geode:latest for integration test service
- Format generated proto stubs for ruff compliance
- Fix bool scalar encoding and transparent oneof in protobuf
- Correct protobuf encoding for QUIC wire protocol

### Changed
- Make PyPI publish automatic for version tags

### Documentation
- Align configuration reference with DSN specification
- Update installation instructions for PyPI

## [0.3.0] - 2025-08-01

### Added
- gRPC transport support (`grpc://host:port`)
- Protobuf wire format replacing JSON protocol
- DSN URL parsing for connection configuration
- Complex type deserialization (NODE, EDGE, PATH)

### Changed
- Replace JSON wire protocol with protobuf
- Remove deprecated `grcp://` and `geode://` schemes

### Fixed
- Lower coverage threshold to 70% for transport code
- Exclude generated proto files from coverage
- Update protobuf to >=6.31.0 for generated proto compatibility

## [0.2.0] - 2025-06-01

### Added
- Security review with 26 findings addressed
- Pre-commit hooks and code quality configuration
- OSS security scanning, SBOM, and release workflows
- OSS governance and project configuration files
- Standalone native benchmark script
- Comprehensive test coverage (68% to 90%)

### Changed
- Refactor CI pipeline to use DevNW CI/CD catalog components
- Update paths after group move to devnw/codepros/geode

## [0.1.0] - 2025-04-01

### Added
- Initial Python client library for Geode graph database
- QUIC+TLS transport implementation using aioquic
- Connection pooling with configurable min/max sizes
- Query builder with fluent API (QueryBuilder, PatternBuilder, PredicateBuilder)
- Value type system with 23 supported types
- Authentication client with RBAC and RLS support
- Input validation module
- Unit tests, integration tests, and property-based tests
- Benchmark suite

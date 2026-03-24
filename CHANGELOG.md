# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

# CLAUDE.md - Developer Guidance

This document provides guidance for Claude Code and developers working on the Geode Python client library.

## Project Overview

**geode-client-python** is an async Python client library for [Geode](https://gitlab.com/devnw/codepros/geode/geode) graph database. It communicates via QUIC+TLS or gRPC using protobuf wire format.

**Status**: Production-ready with comprehensive test coverage
**Python Version**: 3.9+
**Primary Dependencies**: aioquic (QUIC), grpcio (gRPC), protobuf (wire format)

## Quick Reference

### Build & Install

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Install all extras (dev + integration + benchmark + property)
pip install -e ".[dev,integration,benchmark,property]"
```

### Test Commands

```bash
# Run all unit tests (735 tests)
pytest tests/unit/

# Run with coverage
pytest tests/unit/ --cov=geode_client --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_types.py -v

# Run integration tests (requires Docker or external server)
pytest tests/integration/ -m integration

# Run integration tests with specific transport
GEODE_TRANSPORT=quic pytest tests/integration/ -m integration
GEODE_TRANSPORT=grpc pytest tests/integration/ -m integration

# Connect to external server instead of Docker
GEODE_HOST=192.168.1.100 GEODE_PORT=3141 pytest tests/integration/ -m integration

# Run property-based tests
pytest tests/property/ -v

# Run benchmarks
pytest benchmarks/ --benchmark-only

# Run all tests except integration
pytest tests/unit/ tests/property/
```

### Linting Commands

```bash
# Run ruff linter
ruff check geode_client/

# Fix auto-fixable issues
ruff check geode_client/ --fix

# Format code
ruff format geode_client/

# Run type checker
mypy geode_client/
```

## Project Structure

```
geode-client-python/
├── geode_client/           # Main package
│   ├── __init__.py         # Public API exports
│   ├── client.py           # Client, Connection, Page classes
│   ├── transport.py        # Transport abstraction (QUIC, gRPC)
│   ├── proto/              # Generated protobuf code
│   │   ├── __init__.py     # Protobuf message exports
│   │   ├── geode_pb2.py    # Generated protobuf messages
│   │   └── geode_pb2_grpc.py # Generated gRPC stubs
│   ├── types.py            # Value type system + Node/Edge/Path typed values
│   ├── query_builder.py    # QueryBuilder, PatternBuilder, PredicateBuilder
│   ├── pool.py             # ConnectionPool + create_pool_from_dsn factory
│   ├── auth.py             # AuthClient for RBAC/RLS
│   ├── errors.py           # DriverError, NoRowsError, status classifiers
│   ├── retry.py            # RetryPolicy + async retry helper
│   ├── batch.py            # Statement + chunking for batch/pipeline exec
│   ├── schema.py           # parse_schema_fs (read .gql schema files)
│   ├── crypto.py           # AES-256-GCM field-level encryption (Cipher)
│   ├── quote.py            # quote_ident/quote_string/sanitize_graph_name
│   └── validate.py         # Input validation functions
├── proto/                  # Canonical protobuf schema
│   └── geode.proto         # Synced from server
├── scripts/
│   └── generate_proto.sh   # Regenerate protobuf code
├── tests/
│   ├── unit/               # Unit tests (735 tests)
│   │   ├── test_types.py
│   │   ├── test_query_builder.py
│   │   ├── test_pool.py
│   │   ├── test_config.py
│   │   ├── test_transport.py  # DSN parsing tests
│   │   ├── test_protobuf.py   # Protobuf roundtrip tests
│   │   ├── test_error.py
│   │   ├── test_validate.py
│   │   └── test_prepared_statement.py
│   ├── integration/        # Integration tests (119 tests)
│   │   ├── conftest.py     # Docker container management (QUIC + gRPC)
│   │   ├── test_basic_operations.py
│   │   ├── test_node_crud.py
│   │   ├── test_relationships.py
│   │   ├── test_transactions.py
│   │   ├── test_query_operations.py
│   │   ├── test_data_types.py
│   │   └── test_concurrent.py
│   └── property/           # Property-based tests (50 tests)
│       └── test_hypothesis.py
├── benchmarks/             # Performance benchmarks (154 benchmarks)
│   ├── conftest.py
│   ├── bench_types.py
│   ├── bench_builders.py
│   ├── bench_connection.py
│   └── bench_integration.py
├── examples/               # Usage examples
├── setup.py                # Package configuration
├── pytest.ini              # Test configuration
├── mypy.ini                # Type checker configuration
└── CLAUDE.md               # This file
```

## Module Documentation

### geode_client/client.py

Core client functionality:

- **`Client`**: Factory for creating connections. Use `Client.from_url()` for URL-based configuration.
- **`Connection`**: Async context manager for database operations. Supports queries, transactions, and savepoints.
- **`Page`**: Query result container with columns and rows.
- **`Column`**: Column metadata (name, type).
- **`Savepoint`**: Transaction savepoint for partial rollback.
- **`PreparedStatement`**: Client-side prepared statement with parameter extraction.
- **`BatchResult`**: Result container for batch query execution.
- **`QueryPlan`**: Execution plan from `explain()`.
- **`QueryProfile`**: Execution profile from `profile()`.
- **`PlanOperation`**: Individual operation within a query plan.
- **`open_database()`**: Convenience function for URL-based client creation.

**Error Classes**:

- `GeodeError` - Base exception
- `GeodeConnectionError` - Connection failures
- `QueryError` - Query execution failures
- `AuthError` - Authentication failures
- `SecurityWarning` - Warning for insecure operations (e.g., `skip_verify=True`)

### geode_client/transport.py

Transport abstraction layer:

- **`TransportType`**: Enum for transport selection (`QUIC`, `GRPC`)
- **`TransportConfig`**: Configuration dataclass for transport settings
- **`Transport`**: Abstract base class for transports
- **`QuicTransport`**: QUIC+TLS transport implementation (aioquic)
- **`GrpcTransport`**: gRPC transport implementation (grpcio)
- **`parse_dsn()`**: Parse DSN URLs (`quic://`, `grpc://`)
- **`create_transport()`**: Factory function for transport creation
- **`UnsupportedSchemeError`**: Exception for invalid DSN schemes

### geode_client/proto/

Generated protobuf code (from `proto/geode.proto`):

- **Message types**: `ClientPacket`, `ServerPacket`, `HelloRequest`, `ExecuteRequest`, etc.
- **gRPC stubs**: `GeodeServiceStub` for gRPC client
- **Regenerate**: Run `scripts/generate_proto.sh`

### geode_client/types.py

Type system for GQL values:

- **`ValueKind`**: Enum of 26 supported types (NULL, INT, BOOL, STRING, DECIMAL, ARRAY, OBJECT, BYTEA, DATE, TIME, TIMESTAMP, NODE, EDGE, PATH, etc.)
- **`Value`**: Container for typed values with accessors (`as_int`, `as_string`, `as_decimal`, etc.)
- **`Range`**: Range type with lower/upper bounds
- **`decode_value()`**: Converts JSON values to typed `Value` objects

### geode_client/query_builder.py

Fluent query construction:

- **`QueryBuilder`**: Build GQL queries programmatically
  - `.match()`, `.optional_match()`, `.where()`, `.with_()`, `.return_()`
  - `.order_by()`, `.limit()`, `.offset()`, `.create()`, `.merge()`, `.delete()`
  - `.with_param()`, `.with_params()`, `.build()`

- **`PatternBuilder`**: Build graph patterns
  - `.node()`, `.edge()`, `.variable_length()`, `.build()`

- **`PredicateBuilder`**: Build WHERE predicates
  - `.equals()`, `.not_equals()`, `.greater_than()`, `.less_than()`
  - `.is_null()`, `.is_not_null()`, `.in_()`, `.exists()`
  - `.build_and()`, `.build_or()`

- **`EdgeDirection`**: Enum for edge directions (OUTGOING, INCOMING, UNDIRECTED)

### geode_client/pool.py

Connection pooling:

- **`ConnectionPool`**: Manages a pool of connections
  - Constructor: `min_size`, `max_size`, `timeout`, plus connection params
  - `.acquire()` - Get connection from pool (async context manager)
  - `.size`, `.available` - Pool statistics

### geode_client/auth.py

Authentication and authorization:

- **`AuthClient`**: Wraps connection for auth operations
  - `.login()`, `.logout()`, `.create_user()`, `.delete_user()`
  - `.create_role()`, `.assign_role()`, `.revoke_role()`
  - `.create_rls_policy()`, `.check_permission()`

- **`User`**, **`Role`**, **`Permission`**, **`RLSPolicy`**, **`SessionInfo`**: Data classes

### geode_client/validate.py

Input validation:

- `query()` - Validate query strings
- `param_name()` - Validate parameter names
- `hostname()` - Validate hostnames/IPs
- `port()` - Validate port numbers (1-65535)
- `page_size()` - Validate page sizes (1-100,000)
- `dsn_url()` - Validate connection URLs
- `identifier()`, `label()`, `property_name()` - Validate GQL identifiers
- `timeout()`, `pool_size()` - Validate numeric configurations

### geode_client/errors.py

Server error types and classifiers (mirrors Go `errors.go`):

- **`DriverError`**: Carries `code`, `status_class` (ISO/IEC 39075), `message`; `.is_retryable()` (true for 40001/40502)
- **`NoRowsError`**: Raised by `Connection.query_row`/`fetch_one` when the result set is empty
- `is_auth_error()` (28000/08P01), `is_syntax_error()` (42000), `is_retryable_error()`

### geode_client/retry.py

Retry policy and async retry (mirrors Go `retry.go`):

- **`RetryPolicy`**: `max_attempts=3`, `initial_backoff=1.0`, `max_backoff=30.0`, `multiplier=2.0`; `.backoff(attempt)`
- `default_retry_policy()`, `retry(fn, policy)` - retries only retryable errors

### geode_client/batch.py & schema.py

Batch/pipeline execution and schema loading (mirrors Go `batch.go`/`schema.go`):

- **`Statement`**: `{query, params}` pairing for `Connection.batch_exec`/`pipeline_exec`
- `DEFAULT_CHUNK_SIZE=100`, `DEFAULT_MAX_WORKERS=8`
- `parse_schema_fs(path)` - reads `*.gql` files, returns `list[Statement]`

### geode_client/crypto.py

Field-level encryption (mirrors Go `crypto/cipher.go`):

- **`Cipher(master_key)`**: AES-256-GCM with HKDF-SHA256-derived keys
  - `.encrypt()`/`.decrypt()`, `.encrypt_string()`/`.decrypt_string()` (base64), `.hmac_hex()`
- **`CryptoError`**: Raised on key/cipher failures

### geode_client/quote.py

GQL quoting/escaping helpers (mirrors Go `quote.go`):

- `quote_ident()`, `quote_string()`, `sanitize_graph_name()`
- **`InvalidIdentifierError`**, **`InvalidStringError`**

## Wire Protocol Reference

### Transports

**QUIC Transport** (default):

- **Protocol**: QUIC over UDP
- **Port**: 3141 (default)
- **TLS**: Required (TLS 1.3)
- **ALPN**: `geode/1`

**gRPC Transport**:

- **Protocol**: gRPC over HTTP/2
- **Port**: 50051 (default)
- **TLS**: Optional (can be disabled for development)

### Message Format

Protobuf with 4-byte big-endian length prefix:

```
[4 bytes: message length][protobuf message bytes]
```

### DSN URL Formats

```
quic://host:port?param=value   # QUIC transport (default port 3141)
grpc://host:port?param=value   # gRPC transport (default port 50051)
```

### Protobuf Messages

Client messages are wrapped in `ClientPacket` -> `QuicClientMessage`:

- `HelloRequest` - Connection handshake
- `ExecuteRequest` - Execute query with parameters
- `PullRequest` - Fetch results
- `BeginRequest` / `CommitRequest` / `RollbackRequest` - Transaction control
- `PingRequest` - Keep-alive

Server responses are wrapped in `ServerPacket` -> `QuicServerMessage`:

- `HelloResponse` - Handshake response with session ID
- `ExecutionResponse` - Query results (schema, data pages, errors)
- `PullResponse` - Additional result pages
- `PingResponse` - Ping acknowledgment

## Common Patterns

### Basic Query Pattern

```python
from geode_client import Client

async def example():
    client = Client(host="localhost", port=3141, skip_verify=True)

    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 1 AS x")
        value = page.rows[0]["x"].as_int
```

### Transaction Pattern

```python
async with client.connection() as conn:
    await conn.begin()
    try:
        await conn.execute("CREATE (n:Node {id: 1})")
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise
```

### Pool Pattern

```python
from geode_client import ConnectionPool

pool = ConnectionPool(host="localhost", port=3141, min_size=2, max_size=10)

async with pool:
    async with pool.acquire() as conn:
        page, _ = await conn.query("RETURN 1")
```

### Query Builder Pattern

```python
from geode_client import QueryBuilder

query, params = (
    QueryBuilder()
    .match("(n:Person)")
    .where("n.age > $min_age")
    .return_("n.name", "n.age")
    .order_by("n.age DESC")
    .limit(10)
    .with_param("min_age", 25)
    .build()
)
```

### Input Validation Pattern

```python
from geode_client import validate, ValidationError

try:
    validated_query = validate.query(user_input)
    validated_host = validate.hostname(host_input)
    validated_port = validate.port(port_input)
except ValidationError as e:
    print(f"Invalid input: {e}")
```

## Testing Guidelines

### Unit Tests

- Test all public APIs
- Use mocks for network operations
- Cover edge cases and error conditions
- Target 80%+ coverage

```python
import pytest
from geode_client import Value, ValueKind

def test_value_as_int():
    val = Value(kind=ValueKind.INT, int_value=42)
    assert val.as_int == 42

def test_value_type_mismatch():
    val = Value(kind=ValueKind.STRING, str_value="hello")
    with pytest.raises(ValueError):
        _ = val.as_int
```

### Integration Tests

- Require running Geode server (via Docker)
- Use unique identifiers to avoid test interference
- Clean up test data
- Use `count()` for verification (not empty checks)

```python
@pytest.mark.integration
async def test_create_node(connection):
    uid = unique_id()
    await connection.execute(f"CREATE (n:Test {{id: '{uid}'}})")

    page, _ = await connection.query(
        "MATCH (n:Test {id: $id}) RETURN count(n) AS cnt",
        {"id": uid}
    )
    assert page.rows[0]["cnt"].as_int == 1
```

### Property Tests

- Use hypothesis for fuzzing
- Test input validation
- Verify no crashes on arbitrary input

```python
from hypothesis import given, strategies as st

@given(value=st.integers())
def test_decode_int_roundtrip(value):
    result = decode_value(value, "INT")
    assert result.as_int == value
```

## Development Workflow

1. **Create feature branch** from `main`
2. **Write tests first** (TDD recommended)
3. **Implement feature**
4. **Run linters**: `ruff check && mypy`
5. **Run tests**: `pytest tests/unit/`
6. **Update documentation** if needed
7. **Create merge request**

## Performance Characteristics

- **Connection establishment**: ~50-100ms (QUIC handshake)
- **Query latency**: ~2-3ms (localhost)
- **Throughput**: 1000+ queries/second (with pooling)
- **Memory**: Minimal allocations, streaming results

## Troubleshooting

### Import Errors

```bash
pip install aioquic protobuf grpcio
```

### Connection Refused

Ensure Geode server is running:

```bash
# QUIC transport
./geode serve --listen 0.0.0.0:3141

# gRPC transport
./geode serve --grpc-listen 0.0.0.0:50051
```

### TLS Errors

For development, use `skip_verify=True`. For production, provide CA certificate.

For gRPC without TLS (development only):

```python
client = Client.from_url("grpc://localhost:50051?tls=0")
```

### Timeout Errors

Increase timeout or check network connectivity:

```python
pool = ConnectionPool(timeout=60.0, ...)
```

## Dependencies

### Required

- `aioquic>=0.9.0` - QUIC transport implementation
- `protobuf>=6.31.0` - Protobuf wire format
- `grpcio>=1.50.0` - gRPC transport implementation

### Development

- `pytest>=7.0.0` - Testing
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-cov>=4.0.0` - Coverage
- `pytest-benchmark>=4.0.0` - Benchmarks
- `hypothesis>=6.0.0` - Property testing
- `ruff>=0.1.0` - Linting
- `mypy>=1.0.0` - Type checking
- `black>=23.0.0` - Formatting (legacy, ruff preferred)

## Related Documentation

- [Geode Server Documentation](../geode/docs/)
- [UPGRADE_PLAN.md](../UPGRADE_PLAN.md) - Client upgrade roadmap
- [Go Client](../geode-client-go/) - Reference implementation
- [Rust Client](../geode-client-rust/) - High-performance alternative

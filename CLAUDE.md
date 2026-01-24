# CLAUDE.md - Developer Guidance

This document provides guidance for Claude Code and developers working on the Geode Python client library.

## Project Overview

**geode-client-python** is an async Python client library for [Geode](https://gitlab.com/devnw/codepros/geode/geode) graph database. It communicates via QUIC+TLS on port 3141 using a JSON line protocol.

**Status**: Production-ready with comprehensive test coverage
**Python Version**: 3.9+
**Primary Dependencies**: aioquic (QUIC support)

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
# Run all unit tests
pytest tests/unit/

# Run with coverage
pytest tests/unit/ --cov=geode_client --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_types.py -v

# Run integration tests (requires Docker)
pytest tests/integration/ -m integration

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
│   ├── types.py            # Value type system (23 types)
│   ├── query_builder.py    # QueryBuilder, PatternBuilder, PredicateBuilder
│   ├── pool.py             # ConnectionPool for concurrent workloads
│   ├── auth.py             # AuthClient for RBAC/RLS
│   └── validate.py         # Input validation functions
├── tests/
│   ├── unit/               # Unit tests (377 tests)
│   │   ├── test_types.py
│   │   ├── test_query_builder.py
│   │   ├── test_pool.py
│   │   ├── test_config.py
│   │   ├── test_error.py
│   │   └── test_validate.py
│   ├── integration/        # Integration tests (119 tests)
│   │   ├── conftest.py     # Docker container management
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

**Error Classes**:
- `GeodeError` - Base exception
- `GeodeConnectionError` - Connection failures
- `QueryError` - Query execution failures
- `AuthError` - Authentication failures

### geode_client/types.py

Type system for GQL values:

- **`ValueKind`**: Enum of 23 supported types (NULL, INT, BOOL, STRING, DECIMAL, ARRAY, OBJECT, BYTEA, DATE, TIME, TIMESTAMP, etc.)
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

## Wire Protocol Reference

### Transport

- **Protocol**: QUIC over UDP
- **Port**: 3141 (standard) or 8443 (alternative)
- **TLS**: Required (TLS 1.3)
- **ALPN**: `geode/1`

### Message Format

JSON objects, one per line (newline-delimited JSON):

```json
{"type": "MESSAGE_TYPE", "field": "value"}\n
```

### Client Messages

```json
// HELLO - Connection handshake
{"type": "HELLO", "hello_name": "geode-python", "hello_ver": "0.1.0", "conformance": "min", "page_size": 1000}

// RUN_GQL - Execute query
{"type": "RUN_GQL", "text": "RETURN 1 AS x", "params": {"name": "value"}}

// PULL - Fetch results
{"type": "PULL", "request_id": 1, "page_size": 1000}

// Transaction control
{"type": "BEGIN"}
{"type": "COMMIT"}
{"type": "ROLLBACK"}
{"type": "SAVEPOINT", "name": "sp1"}
{"type": "ROLLBACK_TO", "name": "sp1"}
```

### Server Responses

```json
// HELLO response
{"type": "HELLO", "server_name": "geode", "server_ver": "0.18.0"}

// SCHEMA - Column information
{"result": {"type": "SCHEMA", "columns": [{"name": "x", "type": "INT"}]}}

// BINDINGS - Result rows
{"result": {"type": "BINDINGS", "rows": [{"x": 1}], "final": true}}

// ERROR - Error response
{"result": {"type": "ERROR", "code": "SYNTAX_ERROR", "message": "..."}}
```

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
pip install aioquic
```

### Connection Refused

Ensure Geode server is running:
```bash
./geode serve --listen 0.0.0.0:3141
```

### TLS Errors

For development, use `skip_verify=True`. For production, provide CA certificate.

### Timeout Errors

Increase timeout or check network connectivity:
```python
pool = ConnectionPool(timeout=60.0, ...)
```

## Dependencies

### Required
- `aioquic>=0.9.0` - QUIC implementation

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

# Geode Python Client

A modern, async Python client library for [Geode](https://gitlab.com/devnw/codepros/geode/geode) graph database with full GQL (ISO/IEC 39075:2024) support via QUIC+TLS or gRPC.

## Features

- 🚀 **Fully async** with asyncio and type hints
- 🔒 **QUIC + TLS 1.3** for secure, high-performance networking
- 🌐 **gRPC transport** as an alternative to QUIC
- 📝 **Full GQL support** (98.6% ISO compliance)
- 🏗️ **Query builders** for programmatic query construction
- 🔐 **Complete authentication** with RBAC and RLS support
- 🏊 **Connection pooling** for concurrent workloads
- 📊 **Rich type system** including Decimal, temporal types, and advanced types
- 🎯 **Full type hints** for excellent IDE support
- 📦 **Protobuf wire format** for efficient serialization

## Installation

```bash
# Install from PyPI
pip install geode-client
```

For development:

```bash
# Clone and install in editable mode
git clone https://gitlab.com/devnw/codepros/geode/geode-client-python.git
cd geode-client-python
pip install -e ".[dev]"
```

## Requirements

- Python 3.9+
- aioquic >= 0.9.22 (for QUIC transport)
- protobuf >= 6.33.5 (wire format)
- grpcio >= 1.73.1 (for gRPC transport)
- pyOpenSSL >= 26.4.0, cryptography >= 50.0.0
- Running Geode server with QUIC or gRPC enabled

## Quick Start

### Basic Connection

```python
import asyncio
from geode_client import Client


async def main():
    # Create client
    client = Client(host="127.0.0.1", port=3141, skip_verify=True)

    # Execute query
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 1 AS x, 'Hello' AS greeting")

        for row in page.rows:
            x = row["x"].as_int
            greeting = row["greeting"].as_string
            print(f"x={x}, greeting={greeting}")


asyncio.run(main())
```

### Using URL Connection

```python
from geode_client import open_database


async def main():
    # Open database with QUIC transport (default)
    client = open_database("quic://localhost:3141?insecure_tls_skip_verify=true")

    async with client.connection() as conn:
        page, _ = await conn.query("MATCH (n) RETURN n LIMIT 10")
        print(f"Found {len(page.rows)} nodes")


asyncio.run(main())
```

### Using gRPC Transport

```python
from geode_client import open_database


async def main():
    # Open database with gRPC transport
    client = open_database("grpc://localhost:50051")

    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 1 AS x")
        print(f"Result: {page.rows[0]['x'].as_int}")


asyncio.run(main())
```

### Parameterized Queries

```python
async with client.connection() as conn:
    query = "MATCH (p:Person {name: $name}) RETURN p.age AS age"
    params = {"name": "Alice"}

    page, _ = await conn.query(query, params)
    age = page.rows[0]["age"].as_int
    print(f"Alice is {age} years old")
```

### Transactions

```python
async with client.connection() as conn:
    await conn.begin()
    try:
        await conn.execute(
            "CREATE (p:Person {name: $name, age: $age})", {"name": "Bob", "age": 30}
        )
        await conn.commit()
        print("Transaction committed")
    except Exception as e:
        await conn.rollback()
        print(f"Transaction rolled back: {e}")
```

### Savepoints (Partial Rollback)

```python
async with client.connection() as conn:
    await conn.begin()

    # Create initial data
    await conn.execute("CREATE (p:Person {name: 'Alice', age: 30})")

    # Create a savepoint
    sp = await conn.savepoint("before_update")

    # Make changes
    await conn.execute("MATCH (p:Person {name: 'Alice'}) SET p.age = 40")

    # Rollback to savepoint (undoes the age change)
    await conn.rollback_to(sp)

    # Alice's age is still 30
    await conn.commit()
```

### Query Builder

```python
from geode_client import QueryBuilder

query_text, params = (
    QueryBuilder()
    .match("(p:Person {name: $name})-[:KNOWS]->(friend:Person)")
    .where("friend.age > 25")
    .return_("friend.name AS name", "friend.age AS age")
    .order_by("friend.age DESC")
    .limit(10)
    .with_param("name", "Alice")
    .build()
)

page, _ = await conn.query(query_text, params)
```

### Connection Pooling

```python
from geode_client import ConnectionPool

# Create pool
pool = ConnectionPool(
    host="localhost",
    port=3141,
    min_size=2,
    max_size=10,  # default is 3
    skip_verify=True,
)

async with pool:
    # Acquire connection from pool
    async with pool.acquire() as conn:
        page, _ = await conn.query("RETURN 1")

    # Pool automatically manages connection lifecycle
    print(f"Pool size: {pool.size}, available: {pool.available}")
```

### Authentication

```python
from geode_client import AuthClient

async with client.connection() as conn:
    auth = AuthClient(conn)

    # Login
    session = await auth.login("username", "password")
    # Note: Never log or print session tokens in production code
    print(f"Logged in as: {session.username}")
    print(f"Roles: {session.roles}")

    # Create user
    user = await auth.create_user(
        username="newuser",
        email="user@example.com",
        password="secure123",
        roles=["user"],
    )
    print(f"Created user: {user.username}")

    # Check permission
    has_perm = await auth.check_permission(
        user_id=user.id, resource="data", action="read"
    )
    print(f"Has read permission: {has_perm}")

    # Logout
    await auth.logout(session.token)
```

### Pagination

```python
async with client.connection() as conn:
    query = "MATCH (n:Person) RETURN n.name ORDER BY n.name"

    # Get first page
    page, pager = await conn.query(query, page_size=100)

    # Process first page
    for row in page.rows:
        process(row)

    # Get more pages
    async for next_page in pager():
        for row in next_page.rows:
            process(row)
```

## Advanced Features

### Pattern Builder

```python
from geode_client import PatternBuilder, EdgeDirection

pattern = (
    PatternBuilder()
    .node("a", "Person", {"name": "$person1"})
    .edge("knows", "KNOWS", EdgeDirection.UNDIRECTED)
    .variable_length(1, 6)
    .node("b", "Person", {"name": "$person2"})
    .build()
)
# Result: (a:Person {name: $person1})-[knows:KNOWS*1..6]-(b:Person {name: $person2})
```

### Predicate Builder

```python
from geode_client import PredicateBuilder

predicate = (
    PredicateBuilder()
    .greater_than("p.age", "25")
    .is_not_null("p.email")
    .in_("p.role", ["admin", "user"])
    .build_and()
)
# Result: p.age > 25 AND p.email IS NOT NULL AND p.role IN ['admin', 'user']
```

### Row-Level Security (RLS)

```python
from geode_client import RLSPolicy

policy = RLSPolicy(
    name="user_data_policy",
    table="user_data",
    graph="main",
    operation="SELECT",
    permissive=True,
    roles=[1, 2],
    using_expression="owner_id = current_user_id()",
    enabled=True,
    audit_level="READ",
)

policy = await auth.create_rls_policy(policy)
print(f"Created policy: {policy.name} (ID: {policy.id})")
```

## Type System

The client supports all GQL types with proper Python mappings:

```python
# Access typed values
row = page.rows[0]

# Basic types
int_val = row["count"].as_int
str_val = row["name"].as_string
bool_val = row["active"].as_bool
decimal_val = row["price"].as_decimal

# Temporal types
date_val = row["birthdate"].as_date
timestamp_val = row["created_at"].as_datetime

# Complex types
array_val = row["tags"].as_array
object_val = row["metadata"].as_object
bytes_val = row["data"].as_bytes
range_val = row["period"].as_range
```

## Connection Options

### URL Formats (DSN)

> **Note**: See [`geode/docs/DSN.md`](../geode/docs/DSN.md) for the complete DSN specification.

The client supports two transport schemes:

```
quic://host:port?param=value&param2=value2   # QUIC transport (default port 3141)
grpc://host:port?param=value&param2=value2   # gRPC transport (default port 50051)
```

**Examples:**

```python
# QUIC with default port (3141)
client = Client.from_url("quic://localhost")

# QUIC with explicit port and options
client = Client.from_url(
    "quic://geode.example.com:3141?insecure_tls_skip_verify=true&page_size=500"
)

# gRPC with default port (50051)
client = Client.from_url("grpc://localhost")

# gRPC with explicit port and TLS disabled (for local development)
client = Client.from_url("grpc://localhost:50051?tls=0")

# IPv6 support
client = Client.from_url("quic://[::1]:3141")
client = Client.from_url("grpc://[2001:db8::1]:50051")
```

### DSN Query Parameters

These parameters can be used in DSN connection strings (see [DSN specification](../geode/docs/DSN.md)):

| Parameter | Aliases | Type | Default | Description |
|-----------|---------|------|---------|-------------|
| `page_size` | - | int | 1000 | Results page size (1-100,000) |
| `hello_name` | - | string | "geode-python" | Client identification name |
| `hello_ver` | - | string | "0.1.0" | Client version string |
| `conformance` | - | string | "min" | GQL conformance level ("min", "full") |
| `tls` | - | boolean | true | Enable TLS (gRPC only, QUIC always uses TLS) |
| `insecure_tls_skip_verify` | - | boolean | false | Skip TLS certificate verification (**insecure**) |
| `ca` | `ca_cert` | string | - | Path to CA certificate file |
| `cert` | `client_cert` | string | - | Path to client certificate file (for mTLS) |
| `key` | `client_key` | string | - | Path to client private key file (for mTLS) |
| `server_name` | - | string | hostname | SNI server name for TLS |
| `connect_timeout` | `timeout` | int | 30 | Connection timeout in seconds |
| `read_timeout` | - | float | 30 | Per-message read timeout in seconds |
| `idle_timeout` | - | float | 60 | QUIC connection idle timeout in seconds |

### Long-Running Queries

Queries that keep the server busy for a long time need both timeouts raised:
`read_timeout` bounds how long the client waits for a single server message,
while `idle_timeout` bounds how long the underlying QUIC connection may sit
without traffic before it is torn down. Raising only `read_timeout` is not
enough — the connection is closed at `idle_timeout` regardless.

```python
# Allow up to 5 minutes of server-side work per message
client = Client.from_url("quic://localhost:3141?read_timeout=300&idle_timeout=360")

# Same via the Python API
client = Client(host="localhost", port=3141, read_timeout=300.0, idle_timeout=360.0)
```

### Python API Parameters

When using `Client()` constructor directly:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | str | `"127.0.0.1"` | Server hostname or IP address |
| `port` | int | `3141` (QUIC), `50051` (gRPC) | Server port number |
| `transport_type` | TransportType | `QUIC` | Transport protocol (`TransportType.QUIC` or `TransportType.GRPC`) |
| `page_size` | int | `1000` | Results page size (1-100,000) |
| `skip_verify` | bool | `False` | Skip TLS certificate verification (**insecure**) |
| `ca_cert` | str | `None` | Path to CA certificate for server verification |
| `client_cert` | str | `None` | Path to client certificate for mTLS |
| `client_key` | str | `None` | Path to client private key for mTLS |
| `server_name` | str | hostname | SNI server name for TLS |
| `read_timeout` | float | `30.0` | Per-message read timeout (seconds) |
| `idle_timeout` | float | `60.0` | QUIC connection idle timeout (seconds) |

### Pool Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_size` | int | `1` | Minimum connections to maintain |
| `max_size` | int | `10` | Maximum connections allowed |
| `timeout` | float | `30.0` | Connection acquisition timeout (seconds) |

### Example with TLS

```python
client = Client(
    host="geode.example.com",
    port=3141,
    ca_cert="/path/to/ca.crt",
    client_cert="/path/to/client.crt",
    client_key="/path/to/client.key",
    server_name="geode.example.com",
)
```

## Error Handling

The client provides specific exceptions for different error types:

```python
from geode_client import GeodeError, ConnectionError, QueryError, AuthError

try:
    page, _ = await conn.query("INVALID SYNTAX")
except QueryError as e:
    print(f"Query failed: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except AuthError as e:
    print(f"Auth failed: {e}")
except GeodeError as e:
    print(f"Geode error: {e}")
```

## Examples

See the `examples/` directory for complete examples:

- `examples/basic_example.py` - Simple connection and queries
- `examples/advanced_example.py` - Advanced features and patterns
- `examples/quic_example.py` - Comprehensive QUIC client examples
- `examples/transactions_example.py` - Transaction management with savepoints

Run examples:

```bash
python examples/quic_example.py
python examples/transactions_example.py
```

## Development

### Setup Development Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with all dev dependencies
pip install -e ".[dev,integration,benchmark,property]"
```

### Running Tests

The test suite includes unit tests, integration tests, property-based tests, and benchmarks.

```bash
# Run all unit tests (537 tests)
pytest tests/unit/

# Run with coverage report
pytest tests/unit/ --cov=geode_client --cov-report=term-missing

# Run specific test module
pytest tests/unit/test_types.py -v

# Run integration tests (requires Docker or external server, 119 tests)
pytest tests/integration/ -m integration

# Run integration tests with QUIC transport (default)
GEODE_TRANSPORT=quic pytest tests/integration/ -m integration

# Run integration tests with gRPC transport
GEODE_TRANSPORT=grpc pytest tests/integration/ -m integration

# Connect to external server instead of Docker
GEODE_HOST=192.168.1.100 GEODE_PORT=3141 pytest tests/integration/ -m integration

# Run property-based tests (50 tests)
pytest tests/property/ -v

# Run benchmarks (154 benchmarks)
pytest benchmarks/ --benchmark-only

# Run quick benchmark subset
pytest benchmarks/bench_types.py --benchmark-only --benchmark-min-rounds=3
```

### Test Categories

| Category | Location | Count | Description |
|----------|----------|-------|-------------|
| Unit | `tests/unit/` | 537 | Module-level tests with mocks |
| Integration | `tests/integration/` | 119 | End-to-end tests with Docker |
| Property | `tests/property/` | 50 | Hypothesis-based fuzz testing |
| Benchmark | `benchmarks/` | 154 | Performance measurements |

### Code Quality

```bash
# Run ruff linter (preferred)
ruff check geode_client/

# Auto-fix linter issues
ruff check geode_client/ --fix

# Format code with ruff
ruff format geode_client/

# Type checking with mypy
mypy geode_client/

# Run all quality checks
ruff check geode_client/ && ruff format --check geode_client/ && mypy geode_client/
```

## Performance

Both QUIC and gRPC transports provide excellent performance characteristics:

| Metric | Value | Notes |
|--------|-------|-------|
| Connection establishment | ~50-100ms | QUIC handshake + TLS |
| Query latency | ~2-3ms | Localhost, simple queries |
| Throughput | 1000+ q/s | With connection pooling |
| Result parsing | ~0.5ms/1000 rows | Protobuf decoding |

### Performance Tips

- **Use connection pooling** for concurrent workloads
- **Use parameterized queries** to avoid query parsing overhead
- **Set appropriate page sizes** based on result set size
- **Reuse QueryBuilder patterns** instead of creating new instances

### System-Level QUIC Optimizations

For optimal QUIC throughput on high-bandwidth connections, configure UDP buffer sizes at the OS level.

**Linux:**

```bash
# Increase UDP buffer sizes to 7MB
sudo sysctl -w net.core.rmem_max=7340032
sudo sysctl -w net.core.wmem_max=7340032

# Persist across reboots
echo "net.core.rmem_max=7340032" | sudo tee -a /etc/sysctl.d/99-geode-quic.conf
echo "net.core.wmem_max=7340032" | sudo tee -a /etc/sysctl.d/99-geode-quic.conf
```

**BSD/macOS:**

```bash
sudo sysctl -w kern.ipc.maxsockbuf=8441037
```

**GSO (Generic Segmentation Offload)**: Automatically enabled on Linux 4.18+ by aioquic. To disable (not recommended), set `QUIC_GO_DISABLE_GSO=true`.

**Path MTU Discovery**: Enabled by default, probes for optimal packet sizes.

```python
# Good: Reuse pattern with different parameters
pattern = QueryBuilder().match("(n:Person)").where("n.id = $id").return_("n")
for i in range(100):
    query, params = pattern.with_param("id", i).build()

# Good: Use connection pool for concurrent queries
async with ConnectionPool(min_size=5, max_size=20) as pool:
    tasks = [fetch_data(pool, i) for i in range(100)]
    await asyncio.gather(*tasks)
```

## Troubleshooting

### Connection Refused

Ensure Geode server is running:

```bash
# QUIC transport (default port 3141)
./zig-out/bin/geode serve --listen 0.0.0.0:3141

# gRPC transport (default port 50051)
./zig-out/bin/geode serve --grpc-listen 0.0.0.0:50051
```

### TLS Verification Errors

For development, you can skip verification:

```python
# QUIC with TLS verification skipped
client = Client(host="localhost", port=3141, skip_verify=True)

# gRPC with TLS disabled (for local development only)
client = Client.from_url("grpc://localhost:50051?tls=0")
```

For production, provide CA certificate:

```python
client = Client(host="server", port=3141, ca_cert="/path/to/ca.crt")
```

### Import Errors

Ensure all dependencies are installed:

```bash
pip install aioquic protobuf grpcio
```

### gRPC Connection Issues

If gRPC connections fail, check that the gRPC port is exposed and the server is listening:

```python
# Use insecure channel for local development
client = Client.from_url("grpc://localhost:50051?tls=0")
```

## License

Apache License 2.0 - see LICENSE file for details.

## Input Validation

The client includes an input validation module for sanitizing user input:

```python
from geode_client import validate, ValidationError

try:
    # Validate query string
    query = validate.query(user_input)

    # Validate connection parameters
    host = validate.hostname(host_input)
    port = validate.port(port_input)
    page = validate.page_size(page_input)

    # Validate identifiers
    label = validate.label(label_input)
    prop = validate.property_name(prop_input)
except ValidationError as e:
    print(f"Invalid input: {e}")
```

### Available Validators

| Function | Purpose | Example Valid Input |
|----------|---------|---------------------|
| `validate.query()` | Query strings | `"RETURN 1"` |
| `validate.param_name()` | Parameter names | `"user_id"` |
| `validate.hostname()` | Hosts/IPs | `"localhost"`, `"192.168.1.1"` |
| `validate.port()` | Port numbers | `3141` (1-65535) |
| `validate.page_size()` | Page sizes | `1000` (1-100,000) |
| `validate.identifier()` | GQL identifiers | `"node_name"` |
| `validate.label()` | Node/edge labels | `"Person"` |
| `validate.timeout()` | Timeout values | `30.0` (seconds) |

## Contributing

Contributions are welcome! Please follow these guidelines:

### Development Workflow

1. Fork the repository
2. Create a feature branch from `main`
3. Write tests first (TDD recommended)
4. Implement your changes
5. Run all quality checks:

   ```bash
   ruff check geode_client/ && mypy geode_client/ && pytest tests/unit/
   ```

6. Update documentation if needed
7. Submit a merge request

### Code Standards

- **Style**: Follow PEP 8 (enforced by ruff)
- **Types**: Add type hints to all public functions
- **Docs**: Include docstrings with Args, Returns, Raises
- **Tests**: Maintain 80%+ test coverage
- **Commits**: Use clear, descriptive commit messages

## API Reference

### Core Classes

| Class | Description |
|-------|-------------|
| `Client` | Factory for creating connections. Use `Client.from_url()` for URL config. |
| `Connection` | Async context manager for database operations. |
| `Page` | Query result container with columns and rows. |
| `Value` | Typed value container with accessors (`as_int`, `as_string`, etc.) |
| `QueryBuilder` | Fluent interface for building GQL queries. |
| `PatternBuilder` | Builder for graph patterns (nodes, edges). |
| `PredicateBuilder` | Builder for WHERE clause predicates. |
| `ConnectionPool` | Connection pool for concurrent workloads. |
| `AuthClient` | Authentication and authorization operations. |
| `TransportType` | Enum for transport selection (`QUIC`, `GRPC`). |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `GeodeError` | Base exception for all Geode errors |
| `GeodeConnectionError` | Connection establishment failures |
| `QueryError` | Query execution failures |
| `AuthError` | Authentication/authorization failures |
| `ValidationError` | Input validation failures |
| `UnsupportedSchemeError` | Invalid DSN scheme (not `quic://` or `grpc://`) |

For detailed developer documentation, see [CLAUDE.md](CLAUDE.md).

## Related

- [Geode Database](https://gitlab.com/devnw/codepros/geode/geode) - Main database project
- [Go Client](../geode-client-go/) - Production-ready Go client
- [Rust Client](../geode-client-rust/) - High-performance Rust client
- [Zig Client](../geode-client-zig/) - Zig client library

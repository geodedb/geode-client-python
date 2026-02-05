"""
Benchmarks for connection and pool operations.

Tests the performance of:
- Client/Connection construction
- DSN/URL parsing
- Connection configuration
- Pool creation and configuration
- HELLO message building (simulated)

Note: Actual network operations are tested in bench_integration.py
"""

import asyncio
import json
from unittest.mock import MagicMock

import pytest

from geode_client import Client, ConnectionPool
from geode_client.client import Connection

# ============================================================================
# Client construction benchmarks
# ============================================================================


class TestClientConstructionBenchmarks:
    """Benchmarks for Client construction."""

    def test_client_default(self, benchmark):
        """Benchmark creating client with defaults."""
        benchmark(Client)

    def test_client_with_params(self, benchmark):
        """Benchmark creating client with parameters."""

        def create():
            return Client(
                host="geode.example.com",
                port=8443,
                skip_verify=True,
                page_size=500,
            )

        benchmark(create)

    def test_client_from_simple_url(self, benchmark):
        """Benchmark creating client from simple URL."""
        benchmark(Client.from_url, "quic://localhost:3141")

    def test_client_from_url_with_params(self, benchmark):
        """Benchmark creating client from URL with parameters."""
        url = "quic://geode.example.com:8443?skip_verify=true&page_size=1000"
        benchmark(Client.from_url, url)

    def test_client_from_complex_url(self, benchmark):
        """Benchmark creating client from complex URL."""
        url = (
            "quic://geode.example.com:8443?"
            "skip_verify=true&"
            "page_size=2000&"
            "hello_name=my-app&"
            "hello_ver=2.0.0&"
            "conformance=full&"
            "server_name=custom.example.com"
        )
        benchmark(Client.from_url, url)


# ============================================================================
# Connection construction benchmarks
# ============================================================================


class TestConnectionConstructionBenchmarks:
    """Benchmarks for Connection construction."""

    def test_connection_default(self, benchmark):
        """Benchmark creating connection with defaults."""
        benchmark(Connection)

    def test_connection_with_params(self, benchmark):
        """Benchmark creating connection with all parameters."""

        def create():
            return Connection(
                host="geode.example.com",
                port=8443,
                page_size=500,
                hello_name="benchmark-client",
                hello_ver="1.0.0",
                conformance="full",
                ca_cert="/path/to/ca.crt",
                client_cert="/path/to/client.crt",
                client_key="/path/to/client.key",
                skip_verify=False,
                server_name="custom.sni.example.com",
            )

        benchmark(create)

    def test_connection_localhost_normalization(self, benchmark):
        """Benchmark connection with localhost normalization."""
        benchmark(lambda: Connection(host="localhost"))


# ============================================================================
# Pool construction benchmarks
# ============================================================================


class TestPoolConstructionBenchmarks:
    """Benchmarks for ConnectionPool construction."""

    def test_pool_default(self, benchmark):
        """Benchmark creating pool with defaults."""
        benchmark(ConnectionPool)

    def test_pool_with_params(self, benchmark):
        """Benchmark creating pool with parameters."""

        def create():
            return ConnectionPool(
                host="geode.example.com",
                port=8443,
                min_size=5,
                max_size=50,
                timeout=60.0,
                skip_verify=True,
            )

        benchmark(create)

    def test_pool_size_property(self, benchmark):
        """Benchmark accessing pool size property."""
        pool = ConnectionPool()
        benchmark(lambda: pool.size)

    def test_pool_available_property(self, benchmark):
        """Benchmark accessing pool available property."""
        pool = ConnectionPool()
        benchmark(lambda: pool.available)


# ============================================================================
# HELLO message benchmarks
# ============================================================================


class TestHelloMessageBenchmarks:
    """Benchmarks for HELLO message construction."""

    def test_hello_message_simple(self, benchmark):
        """Benchmark building simple HELLO message."""

        def build_hello():
            return json.dumps(
                {
                    "type": "HELLO",
                    "client_name": "geode-python",
                    "client_ver": "0.1.0",
                    "wanted_conformance": "min",
                }
            )

        benchmark(build_hello)

    def test_hello_message_with_page_size(self, benchmark):
        """Benchmark building HELLO message with page_size."""

        def build_hello():
            return json.dumps(
                {
                    "type": "HELLO",
                    "client_name": "geode-python",
                    "client_ver": "0.1.0",
                    "wanted_conformance": "min",
                    "page_size": 1000,
                }
            )

        benchmark(build_hello)

    def test_hello_message_full(self, benchmark):
        """Benchmark building full HELLO message."""

        def build_hello():
            return (
                json.dumps(
                    {
                        "type": "HELLO",
                        "client_name": "my-application",
                        "client_ver": "2.0.0",
                        "wanted_conformance": "full",
                        "page_size": 5000,
                    }
                )
                + "\n"
            )

        benchmark(build_hello)

    def test_hello_message_encode(self, benchmark):
        """Benchmark encoding HELLO message to bytes."""
        msg = (
            json.dumps(
                {
                    "type": "HELLO",
                    "client_name": "geode-python",
                    "client_ver": "0.1.0",
                    "wanted_conformance": "min",
                }
            )
            + "\n"
        )
        benchmark(lambda: msg.encode("utf-8"))


# ============================================================================
# Protocol message benchmarks
# ============================================================================


class TestProtocolMessageBenchmarks:
    """Benchmarks for protocol message construction."""

    def test_run_gql_simple(self, benchmark):
        """Benchmark building simple RUN_GQL message."""

        def build():
            return json.dumps(
                {
                    "type": "RUN_GQL",
                    "text": "RETURN 1 AS x",
                }
            )

        benchmark(build)

    def test_run_gql_with_params(self, benchmark):
        """Benchmark building RUN_GQL with parameters."""

        def build():
            return json.dumps(
                {
                    "type": "RUN_GQL",
                    "text": "RETURN $name AS name, $age AS age",
                    "params": {"name": "Alice", "age": 30},
                }
            )

        benchmark(build)

    def test_run_gql_complex_query(self, benchmark):
        """Benchmark building RUN_GQL with complex query."""
        query = """
            MATCH (p:Person)
            WHERE p.age > $minAge AND p.active = true
            WITH p.city AS city, count(p) AS population
            RETURN city, population
            ORDER BY population DESC
            LIMIT 20
        """

        def build():
            return json.dumps(
                {
                    "type": "RUN_GQL",
                    "text": query,
                    "params": {"minAge": 25},
                }
            )

        benchmark(build)

    def test_pull_message(self, benchmark):
        """Benchmark building PULL message."""

        def build():
            return json.dumps(
                {
                    "type": "PULL",
                    "request_id": 1,
                    "page_size": 1000,
                }
            )

        benchmark(build)

    def test_begin_message(self, benchmark):
        """Benchmark building BEGIN message."""
        benchmark(lambda: json.dumps({"type": "BEGIN"}))

    def test_commit_message(self, benchmark):
        """Benchmark building COMMIT message."""
        benchmark(lambda: json.dumps({"type": "COMMIT"}))

    def test_rollback_message(self, benchmark):
        """Benchmark building ROLLBACK message."""
        benchmark(lambda: json.dumps({"type": "ROLLBACK"}))

    def test_savepoint_message(self, benchmark):
        """Benchmark building SAVEPOINT message."""

        def build():
            return json.dumps(
                {
                    "type": "SAVEPOINT",
                    "name": "sp1",
                }
            )

        benchmark(build)


# ============================================================================
# Response parsing benchmarks
# ============================================================================


class TestResponseParsingBenchmarks:
    """Benchmarks for parsing server responses."""

    def test_parse_hello_response(self, benchmark):
        """Benchmark parsing HELLO response."""
        response = '{"type": "HELLO", "server_name": "geode", "server_ver": "0.18.0"}'
        benchmark(json.loads, response)

    def test_parse_schema_response(self, benchmark):
        """Benchmark parsing SCHEMA response."""
        response = json.dumps(
            {
                "result": {
                    "type": "SCHEMA",
                    "columns": [
                        {"name": "x", "type": "INT"},
                        {"name": "name", "type": "STRING"},
                        {"name": "active", "type": "BOOL"},
                    ],
                }
            }
        )
        benchmark(json.loads, response)

    def test_parse_bindings_small(self, benchmark):
        """Benchmark parsing small BINDINGS response."""
        response = json.dumps(
            {
                "result": {
                    "type": "BINDINGS",
                    "rows": [
                        {"x": 1, "name": "Alice", "active": True},
                    ],
                    "final": True,
                }
            }
        )
        benchmark(json.loads, response)

    def test_parse_bindings_medium(self, benchmark):
        """Benchmark parsing medium BINDINGS response (100 rows)."""
        rows = [{"id": i, "name": f"User_{i}", "value": i * 10} for i in range(100)]
        response = json.dumps(
            {
                "result": {
                    "type": "BINDINGS",
                    "rows": rows,
                    "final": True,
                }
            }
        )
        benchmark(json.loads, response)

    def test_parse_bindings_large(self, benchmark):
        """Benchmark parsing large BINDINGS response (1000 rows)."""
        rows = [{"id": i, "name": f"User_{i}", "value": i * 10} for i in range(1000)]
        response = json.dumps(
            {
                "result": {
                    "type": "BINDINGS",
                    "rows": rows,
                    "final": True,
                }
            }
        )
        benchmark(json.loads, response)

    def test_parse_error_response(self, benchmark):
        """Benchmark parsing ERROR response."""
        response = json.dumps(
            {
                "result": {
                    "type": "ERROR",
                    "code": "SYNTAX_ERROR",
                    "message": "Unexpected token at position 15",
                }
            }
        )
        benchmark(json.loads, response)


# ============================================================================
# Async pool operation benchmarks (simulated)
# ============================================================================


class TestAsyncPoolBenchmarks:
    """Benchmarks for async pool operations (simulated without network)."""

    def test_pool_queue_put(self, benchmark):
        """Benchmark putting connection into pool queue."""
        queue = asyncio.Queue(maxsize=10)
        mock_conn = MagicMock()

        def put_nowait():
            try:
                queue.put_nowait(mock_conn)
                queue.get_nowait()  # Remove to keep queue empty
            except asyncio.QueueFull:
                pass

        benchmark(put_nowait)

    def test_pool_queue_get(self, benchmark):
        """Benchmark getting connection from pool queue."""
        queue = asyncio.Queue(maxsize=10)
        mock_conn = MagicMock()

        def get_nowait():
            queue.put_nowait(mock_conn)
            return queue.get_nowait()

        benchmark(get_nowait)

    def test_pool_lock_acquire_release(self, benchmark):
        """Benchmark lock acquire/release pattern."""
        lock = asyncio.Lock()

        async def acquire_release():
            async with lock:
                pass

        def run():
            asyncio.get_event_loop().run_until_complete(acquire_release())

        # Only run if there's an event loop
        try:
            asyncio.get_event_loop()
            benchmark(run)
        except RuntimeError:
            pytest.skip("No event loop available")

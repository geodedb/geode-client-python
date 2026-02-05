"""
Benchmarks for integration operations requiring a running Geode server.

Tests the performance of:
- Query execution latency
- Result set parsing
- Concurrent query throughput
- Transaction operations
- Connection pool efficiency

Note: These benchmarks require a running Geode server at localhost:3141.
Skip with: pytest benchmarks/bench_integration.py --benchmark-skip
"""

import asyncio
import json

import pytest

from geode_client import Client, ConnectionPool, QueryBuilder

# ============================================================================
# Simulated integration benchmarks (no server required)
# ============================================================================


class TestSimulatedQueryBenchmarks:
    """Benchmarks for query operations using mocked connections."""

    def test_query_preparation(self, benchmark):
        """Benchmark preparing a query (no network)."""

        def prepare():
            query = "MATCH (n:Person) WHERE n.age > $age RETURN n"
            params = {"age": 25}
            return (
                json.dumps(
                    {
                        "type": "RUN_GQL",
                        "text": query,
                        "params": params,
                    }
                )
                + "\n"
            )

        benchmark(prepare)

    def test_query_with_builder(self, benchmark):
        """Benchmark preparing query with builder."""

        def prepare():
            qb = (
                QueryBuilder()
                .match("(n:Person)")
                .where("n.age > $age")
                .return_("n")
                .with_param("age", 25)
            )
            query, params = qb.build()
            return (
                json.dumps(
                    {
                        "type": "RUN_GQL",
                        "text": query,
                        "params": params,
                    }
                )
                + "\n"
            )

        benchmark(prepare)

    def test_result_parsing_small(self, benchmark):
        """Benchmark parsing small result set (10 rows)."""
        rows = [{"id": i, "name": f"User_{i}", "age": 20 + i} for i in range(10)]
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

    def test_result_parsing_medium(self, benchmark):
        """Benchmark parsing medium result set (100 rows)."""
        rows = [{"id": i, "name": f"User_{i}", "age": 20 + i} for i in range(100)]
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

    def test_result_parsing_large(self, benchmark):
        """Benchmark parsing large result set (1000 rows)."""
        rows = [{"id": i, "name": f"User_{i}", "age": 20 + i} for i in range(1000)]
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

    def test_result_parsing_complex_rows(self, benchmark):
        """Benchmark parsing rows with complex data."""
        rows = [
            {
                "id": i,
                "name": f"User_{i}",
                "email": f"user{i}@example.com",
                "age": 20 + i,
                "active": i % 2 == 0,
                "score": f"{85 + (i % 15)}.{i % 100:02d}",
                "tags": ["tag1", "tag2", "tag3"],
                "metadata": {"created": "2024-01-15", "version": i},
            }
            for i in range(100)
        ]
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


# ============================================================================
# Transaction message benchmarks
# ============================================================================


class TestTransactionMessageBenchmarks:
    """Benchmarks for transaction-related message construction."""

    def test_begin_transaction(self, benchmark):
        """Benchmark BEGIN message construction."""
        benchmark(lambda: json.dumps({"type": "BEGIN"}) + "\n")

    def test_commit_transaction(self, benchmark):
        """Benchmark COMMIT message construction."""
        benchmark(lambda: json.dumps({"type": "COMMIT"}) + "\n")

    def test_rollback_transaction(self, benchmark):
        """Benchmark ROLLBACK message construction."""
        benchmark(lambda: json.dumps({"type": "ROLLBACK"}) + "\n")

    def test_savepoint_create(self, benchmark):
        """Benchmark SAVEPOINT message construction."""

        def build():
            return (
                json.dumps(
                    {
                        "type": "SAVEPOINT",
                        "name": "sp1",
                    }
                )
                + "\n"
            )

        benchmark(build)

    def test_savepoint_rollback(self, benchmark):
        """Benchmark ROLLBACK TO SAVEPOINT message."""

        def build():
            return (
                json.dumps(
                    {
                        "type": "ROLLBACK_TO",
                        "name": "sp1",
                    }
                )
                + "\n"
            )

        benchmark(build)

    def test_transaction_sequence(self, benchmark):
        """Benchmark typical transaction message sequence."""

        def build_sequence():
            messages = []
            messages.append(json.dumps({"type": "BEGIN"}) + "\n")
            messages.append(
                json.dumps(
                    {
                        "type": "RUN_GQL",
                        "text": "CREATE (n:Person {name: $name})",
                        "params": {"name": "Alice"},
                    }
                )
                + "\n"
            )
            messages.append(
                json.dumps(
                    {
                        "type": "RUN_GQL",
                        "text": "CREATE (n:Person {name: $name})",
                        "params": {"name": "Bob"},
                    }
                )
                + "\n"
            )
            messages.append(json.dumps({"type": "COMMIT"}) + "\n")
            return messages

        benchmark(build_sequence)


# ============================================================================
# Batch operation benchmarks
# ============================================================================


class TestBatchOperationBenchmarks:
    """Benchmarks for batch operation preparation."""

    def test_batch_create_10(self, benchmark):
        """Benchmark preparing 10 CREATE statements."""

        def build_batch():
            messages = []
            for i in range(10):
                messages.append(
                    json.dumps(
                        {
                            "type": "RUN_GQL",
                            "text": "CREATE (n:Person {name: $name, id: $id})",
                            "params": {"name": f"User_{i}", "id": i},
                        }
                    )
                    + "\n"
                )
            return messages

        benchmark(build_batch)

    def test_batch_create_100(self, benchmark):
        """Benchmark preparing 100 CREATE statements."""

        def build_batch():
            messages = []
            for i in range(100):
                messages.append(
                    json.dumps(
                        {
                            "type": "RUN_GQL",
                            "text": "CREATE (n:Person {name: $name, id: $id})",
                            "params": {"name": f"User_{i}", "id": i},
                        }
                    )
                    + "\n"
                )
            return messages

        benchmark(build_batch)

    def test_batch_with_builder(self, benchmark):
        """Benchmark preparing batch with QueryBuilder."""

        def build_batch():
            messages = []
            for i in range(50):
                qb = (
                    QueryBuilder()
                    .create("(n:Person {name: $name, id: $id})")
                    .return_("n")
                    .with_params({"name": f"User_{i}", "id": i})
                )
                query, params = qb.build()
                messages.append(
                    json.dumps(
                        {
                            "type": "RUN_GQL",
                            "text": query,
                            "params": params,
                        }
                    )
                    + "\n"
                )
            return messages

        benchmark(build_batch)


# ============================================================================
# Result accumulation benchmarks
# ============================================================================


class TestResultAccumulationBenchmarks:
    """Benchmarks for result accumulation patterns."""

    def test_accumulate_rows_append(self, benchmark):
        """Benchmark accumulating rows with list.append."""
        pages = [
            [{"id": i, "name": f"User_{i}"} for i in range(j * 100, (j + 1) * 100)]
            for j in range(10)
        ]

        def accumulate():
            results = []
            for page in pages:
                for row in page:
                    results.append(row)
            return results

        benchmark(accumulate)

    def test_accumulate_rows_extend(self, benchmark):
        """Benchmark accumulating rows with list.extend."""
        pages = [
            [{"id": i, "name": f"User_{i}"} for i in range(j * 100, (j + 1) * 100)]
            for j in range(10)
        ]

        def accumulate():
            results = []
            for page in pages:
                results.extend(page)
            return results

        benchmark(accumulate)

    def test_accumulate_rows_comprehension(self, benchmark):
        """Benchmark accumulating rows with comprehension."""
        pages = [
            [{"id": i, "name": f"User_{i}"} for i in range(j * 100, (j + 1) * 100)]
            for j in range(10)
        ]

        def accumulate():
            return [row for page in pages for row in page]

        benchmark(accumulate)


# ============================================================================
# Connection lifecycle benchmarks (simulated)
# ============================================================================


class TestConnectionLifecycleBenchmarks:
    """Benchmarks for connection lifecycle operations (simulated)."""

    def test_client_context_setup(self, benchmark):
        """Benchmark client context manager setup overhead."""

        def setup():
            client = Client(host="localhost", port=3141)
            # Just measure object creation, not actual connection
            return client

        benchmark(setup)

    def test_pool_context_setup(self, benchmark):
        """Benchmark pool context manager setup overhead."""

        def setup():
            pool = ConnectionPool(
                host="localhost",
                port=3141,
                min_size=2,
                max_size=10,
            )
            return pool

        benchmark(setup)

    def test_multiple_clients(self, benchmark):
        """Benchmark creating multiple client instances."""

        def create_clients():
            clients = []
            for i in range(10):
                clients.append(Client(host="localhost", port=3141))
            return clients

        benchmark(create_clients)


# ============================================================================
# Query builder reuse benchmarks
# ============================================================================


class TestQueryBuilderReuseBenchmarks:
    """Benchmarks for query builder reuse patterns."""

    def test_builder_reuse_same_structure(self, benchmark):
        """Benchmark reusing builder structure with different params."""

        def build_queries():
            results = []
            for i in range(100):
                qb = (
                    QueryBuilder()
                    .match("(n:Person)")
                    .where("n.id = $id")
                    .return_("n")
                    .with_param("id", i)
                )
                results.append(qb.build())
            return results

        benchmark(build_queries)

    def test_template_approach(self, benchmark):
        """Benchmark template-based query building."""
        template = "MATCH (n:Person) WHERE n.id = $id RETURN n"

        def build_queries():
            results = []
            for i in range(100):
                results.append((template, {"id": i}))
            return results

        benchmark(build_queries)

    def test_string_format_approach(self, benchmark):
        """Benchmark string formatting approach (NOT recommended, for comparison)."""

        def build_queries():
            results = []
            for i in range(100):
                # Note: Using params is always recommended over string formatting
                query = f"MATCH (n:Person) WHERE n.id = {i} RETURN n"
                results.append(query)
            return results

        benchmark(build_queries)


# ============================================================================
# Async operation overhead benchmarks
# ============================================================================


class TestAsyncOverheadBenchmarks:
    """Benchmarks measuring async operation overhead."""

    def test_create_coroutine(self, benchmark):
        """Benchmark creating a coroutine object."""

        async def dummy_query():
            return "result"

        benchmark(dummy_query)

    def test_event_creation(self, benchmark):
        """Benchmark asyncio.Event creation."""
        benchmark(asyncio.Event)

    def test_future_creation(self, benchmark):
        """Benchmark asyncio.Future creation (with loop)."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        benchmark(loop.create_future)

    def test_queue_operations(self, benchmark):
        """Benchmark asyncio.Queue put/get operations."""
        queue = asyncio.Queue(maxsize=100)
        item = {"data": "test"}

        def queue_ops():
            queue.put_nowait(item)
            return queue.get_nowait()

        benchmark(queue_ops)


# ============================================================================
# Error response parsing benchmarks
# ============================================================================


class TestErrorParsingBenchmarks:
    """Benchmarks for error response parsing."""

    def test_parse_simple_error(self, benchmark):
        """Benchmark parsing simple error response."""
        error_response = json.dumps(
            {
                "result": {
                    "type": "ERROR",
                    "code": "SYNTAX_ERROR",
                    "message": "Unexpected token",
                }
            }
        )
        benchmark(json.loads, error_response)

    def test_parse_detailed_error(self, benchmark):
        """Benchmark parsing detailed error response."""
        error_response = json.dumps(
            {
                "result": {
                    "type": "ERROR",
                    "code": "SEMANTIC_ERROR",
                    "message": "Unknown property 'nonexistent' on type 'Person'",
                    "position": {"line": 1, "column": 25},
                    "query": "MATCH (n:Person) WHERE n.nonexistent > 0 RETURN n",
                }
            }
        )
        benchmark(json.loads, error_response)

    def test_parse_constraint_error(self, benchmark):
        """Benchmark parsing constraint violation error."""
        error_response = json.dumps(
            {
                "result": {
                    "type": "ERROR",
                    "code": "CONSTRAINT_VIOLATION",
                    "message": "Unique constraint violated for Person.email",
                    "constraint": "unique_person_email",
                    "property": "email",
                    "value": "duplicate@example.com",
                }
            }
        )
        benchmark(json.loads, error_response)


# ============================================================================
# Real integration benchmarks (require server)
# ============================================================================


@pytest.mark.integration
class TestRealIntegrationBenchmarks:
    """
    Benchmarks requiring a real Geode server connection.

    These are marked with @pytest.mark.integration and can be skipped
    when no server is available.

    Run with: pytest benchmarks/bench_integration.py -m integration
    Skip with: pytest benchmarks/bench_integration.py -m "not integration"
    """

    @pytest.fixture
    def event_loop(self):
        """Create event loop for async benchmarks."""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()

    @pytest.mark.skip(reason="Requires running Geode server")
    def test_simple_query_latency(self, benchmark, event_loop):
        """Benchmark simple query execution latency."""

        async def run_query():
            async with Client() as client:
                result = await client.query("RETURN 1 AS x")
                return list(result)

        benchmark(lambda: event_loop.run_until_complete(run_query()))

    @pytest.mark.skip(reason="Requires running Geode server")
    def test_parameterized_query_latency(self, benchmark, event_loop):
        """Benchmark parameterized query execution latency."""

        async def run_query():
            async with Client() as client:
                result = await client.query(
                    "RETURN $x AS x, $y AS y", {"x": 42, "y": "hello"}
                )
                return list(result)

        benchmark(lambda: event_loop.run_until_complete(run_query()))

    @pytest.mark.skip(reason="Requires running Geode server")
    def test_connection_pool_acquire(self, benchmark, event_loop):
        """Benchmark connection pool acquire/release."""

        async def pool_acquire():
            async with ConnectionPool(min_size=5, max_size=10) as pool:
                async with pool.acquire() as conn:
                    result = await conn.query("RETURN 1")
                    return list(result)

        benchmark(lambda: event_loop.run_until_complete(pool_acquire()))

    @pytest.mark.skip(reason="Requires running Geode server")
    def test_transaction_overhead(self, benchmark, event_loop):
        """Benchmark transaction begin/commit overhead."""

        async def run_transaction():
            async with Client() as client, client.transaction() as tx:
                result = await tx.query("RETURN 1")
                return list(result)

        benchmark(lambda: event_loop.run_until_complete(run_transaction()))

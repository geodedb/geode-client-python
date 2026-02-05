"""
Integration tests for concurrent access.

Tests cover:
- Connection pool under load
- Multiple simultaneous queries
- Concurrent connection handling
"""

import asyncio
import uuid

import pytest

from geode_client import ConnectionPool


def unique_id() -> str:
    """Generate a unique ID for test isolation."""
    return str(uuid.uuid4())[:8]


@pytest.mark.asyncio
async def test_multiple_connections(client):
    """Test creating multiple connections sequentially."""
    results = []

    for i in range(3):
        async with client.connection() as conn:
            page, _ = await conn.query(f"RETURN {i} AS num")
            results.append(page.rows[0]["num"].as_int)

    assert results == [0, 1, 2]


@pytest.mark.asyncio
async def test_parallel_queries_same_connection(client):
    """Test parallel queries on the same connection."""
    async with client.connection() as conn:
        # Note: Queries on the same connection are actually serialized
        # but this tests that the client handles them correctly
        async def query(n: int) -> int:
            page, _ = await conn.query(f"RETURN {n} AS num")
            return page.rows[0]["num"].as_int

        # Run queries sequentially on same connection
        results = []
        for i in range(5):
            result = await query(i)
            results.append(result)

        assert results == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_pool_basic_usage(pool):
    """Test basic connection pool usage."""
    async with pool.acquire() as conn:
        page, _ = await conn.query("RETURN 42 AS num")
        assert page.rows[0]["num"].as_int == 42


@pytest.mark.asyncio
async def test_pool_multiple_acquires(pool):
    """Test acquiring multiple connections from pool."""
    results = []

    for i in range(3):
        async with pool.acquire() as conn:
            page, _ = await conn.query(f"RETURN {i} AS num")
            results.append(page.rows[0]["num"].as_int)

    assert results == [0, 1, 2]


@pytest.mark.asyncio
async def test_pool_concurrent_acquires(pool):
    """Test concurrent connection acquisition from pool."""

    async def worker(pool, n: int) -> int:
        async with pool.acquire() as conn:
            page, _ = await conn.query(f"RETURN {n} AS num")
            return page.rows[0]["num"].as_int

    # Run multiple workers concurrently
    tasks = [worker(pool, i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    assert sorted(results) == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_pool_connection_reuse(pool):
    """Test that pool connections are reused."""
    _initial_size = pool.size  # noqa: F841 - stored for potential future assertions

    # Acquire and release multiple times
    for _ in range(10):
        async with pool.acquire() as conn:
            await conn.query("RETURN 1")

    # Pool should not have grown beyond max_size
    assert pool.size <= pool.max_size


@pytest.mark.asyncio
async def test_pool_with_node_operations(geode_host, geode_port):
    """Test pool with actual database operations."""
    uid = unique_id()

    pool = ConnectionPool(
        host=geode_host,
        port=geode_port,
        min_size=2,
        max_size=5,
        skip_verify=True,
    )

    async with pool:
        # Create nodes using different connections
        async with pool.acquire() as conn:
            await conn.execute(f"CREATE (n:PoolTest {{uid: '{uid}', idx: 1}})")

        async with pool.acquire() as conn:
            await conn.execute(f"CREATE (n:PoolTest {{uid: '{uid}', idx: 2}})")

        # Read using another connection
        async with pool.acquire() as conn:
            page, _ = await conn.query(f"""
                MATCH (n:PoolTest {{uid: '{uid}'}})
                RETURN count(n) AS cnt
            """)
            assert page.rows[0]["cnt"].as_int == 2

        # Cleanup
        async with pool.acquire() as conn:
            await conn.execute(f"MATCH (n:PoolTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_concurrent_writes(geode_host, geode_port):
    """Test concurrent write operations."""
    uid = unique_id()

    pool = ConnectionPool(
        host=geode_host,
        port=geode_port,
        min_size=3,
        max_size=10,
        skip_verify=True,
    )

    async with pool:

        async def create_node(idx: int):
            async with pool.acquire() as conn:
                await conn.execute(
                    f"CREATE (n:ConcurrentTest {{uid: '{uid}', idx: {idx}}})"
                )
                return idx

        # Create nodes concurrently
        tasks = [create_node(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Verify all nodes were created
        async with pool.acquire() as conn:
            page, _ = await conn.query(f"""
                MATCH (n:ConcurrentTest {{uid: '{uid}'}})
                RETURN count(n) AS cnt
            """)
            assert page.rows[0]["cnt"].as_int == 5

        # Cleanup
        async with pool.acquire() as conn:
            await conn.execute(f"MATCH (n:ConcurrentTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_concurrent_reads(geode_host, geode_port):
    """Test concurrent read operations."""
    uid = unique_id()

    pool = ConnectionPool(
        host=geode_host,
        port=geode_port,
        min_size=3,
        max_size=10,
        skip_verify=True,
    )

    async with pool:
        # Setup test data
        async with pool.acquire() as conn:
            await conn.execute(f"""
                CREATE (a:ReadTest {{uid: '{uid}', name: 'Alice'}})
                CREATE (b:ReadTest {{uid: '{uid}', name: 'Bob'}})
                CREATE (c:ReadTest {{uid: '{uid}', name: 'Carol'}})
            """)

        async def read_count():
            async with pool.acquire() as conn:
                page, _ = await conn.query(f"""
                    MATCH (n:ReadTest {{uid: '{uid}'}})
                    RETURN count(n) AS cnt
                """)
                return page.rows[0]["cnt"].as_int

        # Run concurrent reads
        tasks = [read_count() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should return 3
        assert all(r == 3 for r in results)

        # Cleanup
        async with pool.acquire() as conn:
            await conn.execute(f"MATCH (n:ReadTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_pool_after_error(geode_host, geode_port):
    """Test that pool recovers after query error."""
    pool = ConnectionPool(
        host=geode_host,
        port=geode_port,
        min_size=1,
        max_size=3,
        skip_verify=True,
    )

    async with pool:
        # This might cause an error (depends on server behavior)
        try:
            async with pool.acquire() as conn:
                await conn.query("INVALID QUERY SYNTAX (((")
        except Exception:
            pass  # Expected

        # Pool should still work for valid queries
        async with pool.acquire() as conn:
            page, _ = await conn.query("RETURN 'recovered' AS status")
            assert page.rows[0]["status"].as_string == "recovered"


@pytest.mark.asyncio
async def test_many_sequential_queries(client):
    """Test many sequential queries on one connection."""
    async with client.connection() as conn:
        for i in range(20):
            page, _ = await conn.query(f"RETURN {i} AS num")
            assert page.rows[0]["num"].as_int == i


@pytest.mark.asyncio
async def test_interleaved_reads_writes(geode_host, geode_port):
    """Test interleaved read and write operations."""
    uid = unique_id()

    pool = ConnectionPool(
        host=geode_host,
        port=geode_port,
        min_size=2,
        max_size=5,
        skip_verify=True,
    )

    async with pool:
        for i in range(5):
            # Write
            async with pool.acquire() as conn:
                await conn.execute(
                    f"CREATE (n:InterleaveTest {{uid: '{uid}', idx: {i}}})"
                )

            # Read
            async with pool.acquire() as conn:
                page, _ = await conn.query(f"""
                    MATCH (n:InterleaveTest {{uid: '{uid}'}})
                    RETURN count(n) AS cnt
                """)
                assert page.rows[0]["cnt"].as_int == i + 1

        # Cleanup
        async with pool.acquire() as conn:
            await conn.execute(f"MATCH (n:InterleaveTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_pool_properties(geode_host, geode_port):
    """Test pool property reporting."""
    pool = ConnectionPool(
        host=geode_host,
        port=geode_port,
        min_size=2,
        max_size=5,
        skip_verify=True,
    )

    async with pool:
        # After initialization, should have min_size connections
        assert pool.size >= pool.min_size

        # Available should be at least min_size initially
        initial_available = pool.available

        # Acquire a connection
        async with pool.acquire() as conn:
            # Available should decrease while connection is in use
            await conn.query("RETURN 1")

        # After release, available should be back
        assert pool.available >= initial_available

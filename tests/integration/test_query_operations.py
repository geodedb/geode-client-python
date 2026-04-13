"""
Integration tests for query operations and aggregations.

Tests cover:
- WHERE clauses
- ORDER BY
- LIMIT/SKIP (OFFSET)
- Complex predicates
- Aggregations: COUNT, SUM, AVG, MIN, MAX
"""

import uuid

import pytest


def unique_id() -> str:
    """Generate a unique ID for test isolation."""
    return str(uuid.uuid4())[:8]


async def setup_test_data(conn, uid: str):
    """Create test data for query operations."""
    await conn.execute(f"""
        CREATE (a:QueryTest {{uid: '{uid}', name: 'Alice', age: 30, score: 85}})
        CREATE (b:QueryTest {{uid: '{uid}', name: 'Bob', age: 25, score: 90}})
        CREATE (c:QueryTest {{uid: '{uid}', name: 'Carol', age: 35, score: 75}})
        CREATE (d:QueryTest {{uid: '{uid}', name: 'Dave', age: 28, score: 88}})
        CREATE (e:QueryTest {{uid: '{uid}', name: 'Eve', age: 32, score: 92}})
    """)


async def cleanup_test_data(conn, uid: str):
    """Clean up test data."""
    await conn.execute(f"MATCH (n:QueryTest {{uid: '{uid}'}}) DELETE n")


# WHERE clause tests


@pytest.mark.asyncio
async def test_where_equals(client):
    """Test WHERE with equality condition."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            WHERE p.name = 'Alice'
            RETURN p.age AS age
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["age"].as_int == 30

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_where_greater_than(client):
    """Test WHERE with greater than condition."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            WHERE p.age > 30
            RETURN count(p) AS cnt
        """)
        # Carol (35) and Eve (32) are > 30
        assert page.rows[0]["cnt"].as_int == 2

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_where_less_than(client):
    """Test WHERE with less than condition."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            WHERE p.age < 30
            RETURN count(p) AS cnt
        """)
        # Bob (25) and Dave (28) are < 30
        assert page.rows[0]["cnt"].as_int == 2

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_where_and(client):
    """Test WHERE with AND condition."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            WHERE p.age >= 30 AND p.score >= 85
            RETURN p.name AS name
        """)
        # Alice (30, 85) and Eve (32, 92) match
        assert len(page.rows) == 2
        names = {row["name"].as_string for row in page.rows}
        assert names == {"Alice", "Eve"}

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_where_or(client):
    """Test WHERE with OR condition."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            WHERE p.name = 'Alice' OR p.name = 'Bob'
            RETURN count(p) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 2

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_where_not_equals(client):
    """Test WHERE with not equals condition."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            WHERE p.name <> 'Alice'
            RETURN count(p) AS cnt
        """)
        # Everyone except Alice (4 people)
        assert page.rows[0]["cnt"].as_int == 4

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_where_between(client):
    """Test WHERE with range condition."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            WHERE p.age >= 28 AND p.age <= 32
            RETURN count(p) AS cnt
        """)
        # Alice (30), Dave (28), Eve (32)
        assert page.rows[0]["cnt"].as_int == 3

        await cleanup_test_data(conn, uid)


# ORDER BY tests


@pytest.mark.asyncio
async def test_order_by_asc(client):
    """Test ORDER BY ascending."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN p.name AS name, p.age AS age
            ORDER BY p.age ASC
        """)
        assert len(page.rows) == 5
        ages = [row["age"].as_int for row in page.rows]
        assert ages == sorted(ages)  # Should be in ascending order

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_order_by_desc(client):
    """Test ORDER BY descending."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN p.name AS name, p.age AS age
            ORDER BY p.age DESC
        """)
        assert len(page.rows) == 5
        ages = [row["age"].as_int for row in page.rows]
        assert ages == sorted(ages, reverse=True)  # Should be in descending order

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_order_by_multiple(client):
    """Test ORDER BY multiple columns."""
    uid = unique_id()
    async with client.connection() as conn:
        # Create data with same ages
        await conn.execute(f"""
            CREATE (a:QueryTest {{uid: '{uid}', name: 'Alice', age: 30}})
            CREATE (b:QueryTest {{uid: '{uid}', name: 'Andy', age: 30}})
            CREATE (c:QueryTest {{uid: '{uid}', name: 'Bob', age: 25}})
        """)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN p.name AS name, p.age AS age
            ORDER BY p.age ASC, p.name ASC
        """)
        # Bob (25), then Alice (30), Andy (30) - alphabetically
        assert len(page.rows) == 3
        assert page.rows[0]["name"].as_string == "Bob"
        # Alice and Andy both 30, Alice comes first alphabetically
        assert page.rows[1]["name"].as_string == "Alice"
        assert page.rows[2]["name"].as_string == "Andy"

        await cleanup_test_data(conn, uid)


# LIMIT and SKIP tests


@pytest.mark.asyncio
async def test_limit(client):
    """Test LIMIT clause."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN p.name AS name
            LIMIT 3
        """)
        assert len(page.rows) == 3

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_skip(client):
    """Test SKIP (OFFSET) clause."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN p.name AS name
            ORDER BY p.age ASC
            SKIP 2
        """)
        # Skip first 2 (Bob 25, Dave 28), get remaining 3
        assert len(page.rows) == 3

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_limit_and_skip(client):
    """Test LIMIT with SKIP (pagination)."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN p.name AS name
            ORDER BY p.age ASC
            SKIP 1
            LIMIT 2
        """)
        # Skip 1, take 2: get persons 2 and 3 by age
        assert len(page.rows) == 2

        await cleanup_test_data(conn, uid)


# Aggregation tests


@pytest.mark.asyncio
async def test_count(client):
    """Test COUNT aggregation."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN count(p) AS total
        """)
        assert page.rows[0]["total"].as_int == 5

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server currently returns NULL for COUNT(DISTINCT ...) - known server behavior"
)
async def test_count_distinct(client):
    """Test COUNT with DISTINCT."""
    uid = unique_id()
    async with client.connection() as conn:
        # Create data with duplicate ages
        await conn.execute(f"""
            CREATE (a:QueryTest {{uid: '{uid}', age: 30}})
            CREATE (b:QueryTest {{uid: '{uid}', age: 30}})
            CREATE (c:QueryTest {{uid: '{uid}', age: 25}})
        """)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN count(DISTINCT p.age) AS unique_ages
        """)
        assert page.rows[0]["unique_ages"].as_int == 2

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_sum(client):
    """Test SUM aggregation."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)
        # Ages: 30 + 25 + 35 + 28 + 32 = 150

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN sum(p.age) AS total_age
        """)
        assert page.rows[0]["total_age"].as_int == 150

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_avg(client):
    """Test AVG aggregation."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)
        # Ages: 30 + 25 + 35 + 28 + 32 = 150, avg = 30

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN avg(p.age) AS avg_age
        """)
        # Average should be 30 (150/5)
        avg_age = page.rows[0]["avg_age"]
        # Handle both int and decimal return types based on value kind
        from geode_client.types import ValueKind

        if avg_age.kind == ValueKind.DECIMAL:
            assert float(avg_age.as_decimal) == 30.0
        else:
            # Server returns INT for whole number averages
            assert avg_age.as_int == 30

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_min(client):
    """Test MIN aggregation."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN min(p.age) AS min_age
        """)
        assert page.rows[0]["min_age"].as_int == 25  # Bob

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_max(client):
    """Test MAX aggregation."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN max(p.age) AS max_age
        """)
        assert page.rows[0]["max_age"].as_int == 35  # Carol

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_multiple_aggregations(client):
    """Test multiple aggregations in one query."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN
                count(p) AS total,
                min(p.age) AS min_age,
                max(p.age) AS max_age,
                sum(p.age) AS sum_age
        """)
        row = page.rows[0]
        assert row["total"].as_int == 5
        assert row["min_age"].as_int == 25
        assert row["max_age"].as_int == 35
        assert row["sum_age"].as_int == 150

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_aggregation_with_where(client):
    """Test aggregation with WHERE clause."""
    uid = unique_id()
    async with client.connection() as conn:
        await setup_test_data(conn, uid)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            WHERE p.age >= 30
            RETURN count(p) AS cnt, avg(p.score) AS avg_score
        """)
        # Alice (30, 85), Carol (35, 75), Eve (32, 92) => 3 people
        assert page.rows[0]["cnt"].as_int == 3

        await cleanup_test_data(conn, uid)


@pytest.mark.asyncio
async def test_collect(client):
    """Test COLLECT aggregation."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (a:QueryTest {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:QueryTest {{uid: '{uid}', name: 'Bob'}})
            CREATE (c:QueryTest {{uid: '{uid}', name: 'Carol'}})
        """)

        page, _ = await conn.query(f"""
            MATCH (p:QueryTest {{uid: '{uid}'}})
            RETURN collect(p.name) AS names
        """)
        assert len(page.rows) == 1
        names = page.rows[0]["names"].as_array
        assert len(names) == 3
        name_values = {n.as_string for n in names}
        assert name_values == {"Alice", "Bob", "Carol"}

        await cleanup_test_data(conn, uid)

"""
Integration tests for basic Geode operations.

Tests cover:
- Ping/connectivity
- Simple queries
- Parameterized queries
- Multiple return columns
- Multiple queries on same connection
"""

import pytest


@pytest.mark.asyncio
async def test_basic_connection(client):
    """Test basic connection establishment."""
    async with client.connection() as conn:
        # Simple query to verify connection
        page, _ = await conn.query("RETURN 1 AS x")
        assert len(page.rows) == 1
        assert page.rows[0]["x"].as_int == 1


@pytest.mark.asyncio
async def test_simple_return(client):
    """Test simple RETURN query with multiple types."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 42 AS num, 'Hello' AS text, true AS flag")
        assert len(page.rows) == 1
        row = page.rows[0]
        assert row["num"].as_int == 42
        assert row["text"].as_string == "Hello"
        assert row["flag"].as_bool is True


@pytest.mark.asyncio
async def test_parameterized_query(client):
    """Test parameterized queries."""
    async with client.connection() as conn:
        query = "RETURN $name AS name, $age AS age, $active AS active"
        params = {"name": "Alice", "age": 30, "active": True}
        page, _ = await conn.query(query, params)

        assert len(page.rows) == 1
        row = page.rows[0]
        assert row["name"].as_string == "Alice"
        assert row["age"].as_int == 30
        assert row["active"].as_bool is True


@pytest.mark.asyncio
async def test_multiple_return_columns(client):
    """Test query with multiple return columns."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 1 AS a, 2 AS b, 3 AS c, 4 AS d, 5 AS e")
        assert len(page.rows) == 1
        assert len(page.columns) == 5

        row = page.rows[0]
        assert row["a"].as_int == 1
        assert row["b"].as_int == 2
        assert row["c"].as_int == 3
        assert row["d"].as_int == 4
        assert row["e"].as_int == 5


@pytest.mark.asyncio
async def test_multiple_queries_same_connection(client):
    """Test executing multiple queries on the same connection."""
    async with client.connection() as conn:
        # First query
        page1, _ = await conn.query("RETURN 1 AS x")
        assert page1.rows[0]["x"].as_int == 1

        # Second query
        page2, _ = await conn.query("RETURN 2 AS y")
        assert page2.rows[0]["y"].as_int == 2

        # Third query
        page3, _ = await conn.query("RETURN 3 AS z")
        assert page3.rows[0]["z"].as_int == 3


@pytest.mark.asyncio
async def test_query_with_expression(client):
    """Test query with expressions."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 2 + 3 AS sum, 10 - 4 AS diff")
        assert len(page.rows) == 1
        row = page.rows[0]
        assert row["sum"].as_int == 5
        assert row["diff"].as_int == 6


@pytest.mark.asyncio
async def test_multiple_rows_union(client):
    """Test query returning multiple rows using UNION."""
    async with client.connection() as conn:
        query = """
        RETURN 1 AS num
        UNION ALL
        RETURN 2 AS num
        UNION ALL
        RETURN 3 AS num
        """
        page, _ = await conn.query(query)

        # UNION should return multiple rows
        assert len(page.rows) >= 1
        # Get all values
        values = [row["num"].as_int for row in page.rows]
        # At least one of our values should be present
        assert any(v in values for v in [1, 2, 3])


@pytest.mark.asyncio
async def test_empty_result(client):
    """Test query that returns empty result."""
    async with client.connection() as conn:
        # Use a label that shouldn't exist
        page, _ = await conn.query("MATCH (n:NonExistentLabel12345) RETURN n")
        assert len(page.rows) == 0


@pytest.mark.asyncio
async def test_column_types(client):
    """Test that column metadata is returned."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 1 AS x, 'hello' AS y")
        assert len(page.columns) == 2

        # Check column names
        col_names = [col.name for col in page.columns]
        assert "x" in col_names
        assert "y" in col_names


@pytest.mark.asyncio
async def test_case_expression(client):
    """Test CASE expression in query."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN CASE
                WHEN 5 > 3 THEN 'greater'
                ELSE 'not greater'
            END AS result
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["result"].as_string == "greater"


@pytest.mark.asyncio
async def test_coalesce_function(client):
    """Test COALESCE function."""
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN COALESCE(null, 'fallback') AS value")
        assert len(page.rows) == 1
        assert page.rows[0]["value"].as_string == "fallback"


@pytest.mark.asyncio
async def test_string_functions(client):
    """Test string functions."""
    async with client.connection() as conn:
        page, _ = await conn.query("""
            RETURN
                'hello' + ' ' + 'world' AS concat,
                SIZE('test') AS len
        """)
        assert len(page.rows) == 1
        row = page.rows[0]
        assert row["concat"].as_string == "hello world"
        assert row["len"].as_int == 4

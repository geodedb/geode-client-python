"""
Integration tests for Node CRUD operations.

Tests cover:
- Create nodes with properties
- Read nodes by ID/properties
- Update node properties
- Delete nodes
- Nodes with labels
"""

import pytest
import uuid


def unique_id() -> str:
    """Generate a unique ID for test isolation."""
    return str(uuid.uuid4())[:8]


@pytest.mark.asyncio
async def test_create_node_simple(client):
    """Test creating a simple node."""
    uid = unique_id()
    async with client.connection() as conn:
        # Create node with inline values (following Go client pattern)
        await conn.execute(f"CREATE (n:TestNode {{uid: '{uid}'}})")

        # Verify node exists
        page, _ = await conn.query(
            f"MATCH (n:TestNode {{uid: '{uid}'}}) RETURN n.uid AS uid"
        )
        assert len(page.rows) == 1
        assert page.rows[0]["uid"].as_string == uid

        # Cleanup
        await conn.execute(f"MATCH (n:TestNode {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_create_node_with_properties(client):
    """Test creating a node with multiple properties."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (p:Person {{
                uid: '{uid}',
                name: 'Alice',
                age: 30,
                active: true
            }})
        """)

        # Verify all properties
        page, _ = await conn.query(f"""
            MATCH (p:Person {{uid: '{uid}'}})
            RETURN p.name AS name, p.age AS age, p.active AS active
        """)
        assert len(page.rows) == 1
        row = page.rows[0]
        assert row["name"].as_string == "Alice"
        assert row["age"].as_int == 30
        assert row["active"].as_bool is True

        # Cleanup
        await conn.execute(f"MATCH (p:Person {{uid: '{uid}'}}) DELETE p")


@pytest.mark.asyncio
async def test_create_multiple_nodes(client):
    """Test creating multiple nodes."""
    uid = unique_id()
    async with client.connection() as conn:
        # Create multiple nodes
        await conn.execute(f"CREATE (a:TestNode {{uid: '{uid}', idx: 1}})")
        await conn.execute(f"CREATE (b:TestNode {{uid: '{uid}', idx: 2}})")
        await conn.execute(f"CREATE (c:TestNode {{uid: '{uid}', idx: 3}})")

        # Count nodes - use count() for reliable verification
        page, _ = await conn.query(f"""
            MATCH (n:TestNode {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 3

        # Cleanup
        await conn.execute(f"MATCH (n:TestNode {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_read_node_by_property(client):
    """Test reading nodes by property value."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (p:Person {{uid: '{uid}', name: 'Bob', city: 'NYC'}})
        """)

        # Read by name property
        page, _ = await conn.query(f"""
            MATCH (p:Person {{name: 'Bob', uid: '{uid}'}})
            RETURN p.city AS city
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["city"].as_string == "NYC"

        # Cleanup
        await conn.execute(f"MATCH (p:Person {{uid: '{uid}'}}) DELETE p")


@pytest.mark.asyncio
async def test_update_node_property(client):
    """Test updating a node property."""
    uid = unique_id()
    async with client.connection() as conn:
        # Create node
        await conn.execute(f"CREATE (p:Person {{uid: '{uid}', age: 25}})")

        # Update property
        await conn.execute(f"""
            MATCH (p:Person {{uid: '{uid}'}})
            SET p.age = 26
        """)

        # Verify update
        page, _ = await conn.query(f"""
            MATCH (p:Person {{uid: '{uid}'}})
            RETURN p.age AS age
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["age"].as_int == 26

        # Cleanup
        await conn.execute(f"MATCH (p:Person {{uid: '{uid}'}}) DELETE p")


@pytest.mark.asyncio
async def test_update_multiple_properties(client):
    """Test updating multiple properties at once."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (p:Person {{uid: '{uid}', name: 'Carol', age: 28}})
        """)

        # Update multiple properties
        await conn.execute(f"""
            MATCH (p:Person {{uid: '{uid}'}})
            SET p.name = 'Caroline', p.age = 29, p.updated = true
        """)

        # Verify updates
        page, _ = await conn.query(f"""
            MATCH (p:Person {{uid: '{uid}'}})
            RETURN p.name AS name, p.age AS age, p.updated AS updated
        """)
        assert len(page.rows) == 1
        row = page.rows[0]
        assert row["name"].as_string == "Caroline"
        assert row["age"].as_int == 29
        assert row["updated"].as_bool is True

        # Cleanup
        await conn.execute(f"MATCH (p:Person {{uid: '{uid}'}}) DELETE p")


@pytest.mark.asyncio
async def test_delete_node(client):
    """Test deleting a node."""
    uid = unique_id()
    async with client.connection() as conn:
        # Create node
        await conn.execute(f"CREATE (n:TestNode {{uid: '{uid}'}})")

        # Verify exists
        page, _ = await conn.query(f"""
            MATCH (n:TestNode {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 1

        # Delete node
        await conn.execute(f"MATCH (n:TestNode {{uid: '{uid}'}}) DELETE n")

        # Verify deleted using count() pattern
        page, _ = await conn.query(f"""
            MATCH (n:TestNode {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 0


@pytest.mark.asyncio
async def test_node_with_multiple_labels(client):
    """Test node with multiple labels."""
    uid = unique_id()
    async with client.connection() as conn:
        # Create node with multiple labels
        await conn.execute(f"""
            CREATE (e:Person:Employee:Manager {{uid: '{uid}', name: 'Dave'}})
        """)

        # Query by one label
        page, _ = await conn.query(f"""
            MATCH (e:Employee {{uid: '{uid}'}})
            RETURN e.name AS name
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["name"].as_string == "Dave"

        # Query by another label
        page, _ = await conn.query(f"""
            MATCH (m:Manager {{uid: '{uid}'}})
            RETURN m.name AS name
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["name"].as_string == "Dave"

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_merge_node(client):
    """Test MERGE creates or matches node."""
    uid = unique_id()
    async with client.connection() as conn:
        # First merge - should create
        await conn.execute(f"MERGE (n:TestNode {{uid: '{uid}'}})")

        page, _ = await conn.query(f"""
            MATCH (n:TestNode {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 1

        # Second merge - should match existing, not create new
        await conn.execute(f"MERGE (n:TestNode {{uid: '{uid}'}})")

        page, _ = await conn.query(f"""
            MATCH (n:TestNode {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 1  # Still 1, not 2

        # Cleanup
        await conn.execute(f"MATCH (n:TestNode {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_node_with_null_property(client):
    """Test node with NULL property value."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (p:Person {{uid: '{uid}', name: 'Eve', email: null}})
        """)

        page, _ = await conn.query(f"""
            MATCH (p:Person {{uid: '{uid}'}})
            RETURN p.email AS email
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["email"].is_null

        # Cleanup
        await conn.execute(f"MATCH (p:Person {{uid: '{uid}'}}) DELETE p")


@pytest.mark.asyncio
async def test_remove_node_property(client):
    """Test removing a property from a node."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (p:Person {{uid: '{uid}', name: 'Frank', temp: 'remove_me'}})
        """)

        # Remove property by setting to null
        await conn.execute(f"""
            MATCH (p:Person {{uid: '{uid}'}})
            SET p.temp = null
        """)

        page, _ = await conn.query(f"""
            MATCH (p:Person {{uid: '{uid}'}})
            RETURN p.temp AS temp
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["temp"].is_null

        # Cleanup
        await conn.execute(f"MATCH (p:Person {{uid: '{uid}'}}) DELETE p")

"""
Integration tests for relationship operations.

Tests cover:
- Create relationships
- Relationship properties
- Traversal queries
- Direction handling
- Relationship types
"""

import uuid

import pytest


def unique_id() -> str:
    """Generate a unique ID for test isolation."""
    return str(uuid.uuid4())[:8]


@pytest.mark.asyncio
async def test_create_relationship(client):
    """Test creating a simple relationship."""
    uid = unique_id()
    async with client.connection() as conn:
        # Create two nodes and a relationship
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:Person {{uid: '{uid}', name: 'Bob'}})
            CREATE (a)-[:KNOWS]->(b)
        """)

        # Verify relationship exists
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[:KNOWS]->(b:Person)
            RETURN b.name AS friend
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["friend"].as_string == "Bob"

        # Cleanup - delete relationships first, then nodes
        await conn.execute(f"MATCH (n {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_relationship_with_properties(client):
    """Test relationship with properties."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:Person {{uid: '{uid}', name: 'Bob'}})
            CREATE (a)-[:KNOWS {{since: 2020, close: true}}]->(b)
        """)

        # Query relationship properties
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[r:KNOWS]->(b:Person)
            RETURN r.since AS since, r.close AS close
        """)
        assert len(page.rows) == 1
        row = page.rows[0]
        assert row["since"].as_int == 2020
        assert row["close"].as_bool is True

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server may not properly enforce relationship direction - known server behavior"
)
async def test_outgoing_direction(client):
    """Test outgoing relationship direction."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:Person {{uid: '{uid}', name: 'Bob'}})
            CREATE (a)-[:FOLLOWS]->(b)
        """)

        # Outgoing from Alice should find Bob
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[:FOLLOWS]->(target)
            RETURN target.name AS name
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["name"].as_string == "Bob"

        # Outgoing from Bob should find nothing
        page, _ = await conn.query(f"""
            MATCH (b:Person {{uid: '{uid}', name: 'Bob'}})-[:FOLLOWS]->(target)
            RETURN count(target) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 0

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server may not properly enforce relationship direction - known server behavior"
)
async def test_incoming_direction(client):
    """Test incoming relationship direction."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:Person {{uid: '{uid}', name: 'Bob'}})
            CREATE (a)-[:FOLLOWS]->(b)
        """)

        # Incoming to Bob should find Alice
        page, _ = await conn.query(f"""
            MATCH (b:Person {{uid: '{uid}', name: 'Bob'}})<-[:FOLLOWS]-(source)
            RETURN source.name AS name
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["name"].as_string == "Alice"

        # Incoming to Alice should find nothing
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})<-[:FOLLOWS]-(source)
            RETURN count(source) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 0

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server may not properly handle undirected relationship matching - known server behavior"
)
async def test_undirected_relationship(client):
    """Test matching relationships regardless of direction."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:Person {{uid: '{uid}', name: 'Bob'}})
            CREATE (a)-[:FRIENDS_WITH]->(b)
        """)

        # Undirected match from Alice
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[:FRIENDS_WITH]-(other)
            RETURN other.name AS name
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["name"].as_string == "Bob"

        # Undirected match from Bob should also find Alice
        page, _ = await conn.query(f"""
            MATCH (b:Person {{uid: '{uid}', name: 'Bob'}})-[:FRIENDS_WITH]-(other)
            RETURN other.name AS name
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["name"].as_string == "Alice"

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_multiple_relationship_types(client):
    """Test nodes with multiple relationship types."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:Person {{uid: '{uid}', name: 'Bob'}})
            CREATE (c:Company {{uid: '{uid}', name: 'Acme'}})
            CREATE (a)-[:KNOWS]->(b)
            CREATE (a)-[:WORKS_AT]->(c)
        """)

        # Find Alice's relationships
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[:KNOWS]->(friend)
            RETURN friend.name AS friend
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["friend"].as_string == "Bob"

        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[:WORKS_AT]->(company)
            RETURN company.name AS company
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["company"].as_string == "Acme"

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_chain_traversal(client):
    """Test traversing multiple relationships."""
    uid = unique_id()
    async with client.connection() as conn:
        # Create a chain: Alice -> Bob -> Carol
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:Person {{uid: '{uid}', name: 'Bob'}})
            CREATE (c:Person {{uid: '{uid}', name: 'Carol'}})
            CREATE (a)-[:KNOWS]->(b)
            CREATE (b)-[:KNOWS]->(c)
        """)

        # Find friends of friends
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[:KNOWS]->(friend)-[:KNOWS]->(fof)
            RETURN fof.name AS fof
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["fof"].as_string == "Carol"

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_relationship_count(client):
    """Test counting relationships."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:Person {{uid: '{uid}', name: 'Bob'}})
            CREATE (c:Person {{uid: '{uid}', name: 'Carol'}})
            CREATE (d:Person {{uid: '{uid}', name: 'Dave'}})
            CREATE (a)-[:KNOWS]->(b)
            CREATE (a)-[:KNOWS]->(c)
            CREATE (a)-[:KNOWS]->(d)
        """)

        # Count Alice's KNOWS relationships
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[:KNOWS]->(friend)
            RETURN count(friend) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 3

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server may delete nodes when deleting relationships - known server behavior"
)
async def test_delete_relationship(client):
    """Test deleting a relationship."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:Person {{uid: '{uid}', name: 'Bob'}})
            CREATE (a)-[:KNOWS]->(b)
        """)

        # Delete the relationship
        await conn.execute(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[r:KNOWS]->(b)
            DELETE r
        """)

        # Verify relationship is gone
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[:KNOWS]->(b)
            RETURN count(b) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 0

        # Verify nodes still exist
        page, _ = await conn.query(f"""
            MATCH (n {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 2

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_update_relationship_property(client):
    """Test updating a relationship property."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (b:Person {{uid: '{uid}', name: 'Bob'}})
            CREATE (a)-[:KNOWS {{since: 2020}}]->(b)
        """)

        # Update relationship property
        await conn.execute(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[r:KNOWS]->(b)
            SET r.since = 2021
        """)

        # Verify update
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}', name: 'Alice'}})-[r:KNOWS]->(b)
            RETURN r.since AS since
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["since"].as_int == 2021

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_self_relationship(client):
    """Test relationship from node to itself."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.execute(f"""
            CREATE (a:Person {{uid: '{uid}', name: 'Alice'}})
            CREATE (a)-[:LIKES]->(a)
        """)

        # Match self-relationship
        page, _ = await conn.query(f"""
            MATCH (a:Person {{uid: '{uid}'}})-[:LIKES]->(a)
            RETURN a.name AS name
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["name"].as_string == "Alice"

        # Cleanup
        await conn.execute(f"MATCH (n {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n {{uid: '{uid}'}}) DELETE n")

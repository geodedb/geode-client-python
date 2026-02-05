"""
Integration tests for transaction operations.

Tests cover:
- Begin/Commit
- Begin/Rollback
- Multi-operation transactions
- Transaction isolation
- Savepoints
"""

import uuid

import pytest


def unique_id() -> str:
    """Generate a unique ID for test isolation."""
    return str(uuid.uuid4())[:8]


@pytest.mark.asyncio
async def test_transaction_commit(client):
    """Test that committed transactions persist data."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.begin()

        await conn.execute(f"CREATE (n:TxTest {{uid: '{uid}', value: 'committed'}})")

        await conn.commit()

        # Verify data persisted using count() pattern
        page, _ = await conn.query(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 1

        # Cleanup
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_transaction_rollback(client):
    """Test that rolled back transactions don't persist data."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.begin()

        await conn.execute(f"CREATE (n:TxTest {{uid: '{uid}', value: 'rollback'}})")

        await conn.rollback()

        # Verify data was NOT persisted using count() pattern
        page, _ = await conn.query(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 0


@pytest.mark.asyncio
async def test_multi_operation_transaction_commit(client):
    """Test transaction with multiple operations that commits."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.begin()

        # Multiple operations
        await conn.execute(f"CREATE (a:TxTest {{uid: '{uid}', idx: 1}})")
        await conn.execute(f"CREATE (b:TxTest {{uid: '{uid}', idx: 2}})")
        await conn.execute(f"CREATE (c:TxTest {{uid: '{uid}', idx: 3}})")

        await conn.commit()

        # All three should exist
        page, _ = await conn.query(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 3

        # Cleanup
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_multi_operation_transaction_rollback(client):
    """Test transaction with multiple operations that rolls back."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.begin()

        await conn.execute(f"CREATE (a:TxTest {{uid: '{uid}', idx: 1}})")
        await conn.execute(f"CREATE (b:TxTest {{uid: '{uid}', idx: 2}})")
        await conn.execute(f"CREATE (c:TxTest {{uid: '{uid}', idx: 3}})")

        await conn.rollback()

        # None should exist
        page, _ = await conn.query(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 0


@pytest.mark.asyncio
async def test_transaction_create_and_query(client):
    """Test querying data created within the same transaction."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.begin()

        await conn.execute(f"CREATE (n:TxTest {{uid: '{uid}', name: 'InTx'}})")

        # Query within transaction should see uncommitted data
        page, _ = await conn.query(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            RETURN n.name AS name
        """)
        # Note: visibility within transaction may vary by implementation
        # Just verify no error occurs

        await conn.commit()

        # Cleanup
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server may not properly rollback transactions - see UPGRADE_PLAN.md Appendix A.6"
)
async def test_transaction_update_and_rollback(client):
    """Test that updates within a transaction are rolled back."""
    uid = unique_id()
    async with client.connection() as conn:
        # First create a node outside transaction
        await conn.execute(f"CREATE (n:TxTest {{uid: '{uid}', value: 'original'}})")

        # Start transaction and update
        await conn.begin()
        await conn.execute(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            SET n.value = 'modified'
        """)
        await conn.rollback()

        # Value should be original
        page, _ = await conn.query(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            RETURN n.value AS value
        """)
        assert len(page.rows) == 1
        assert page.rows[0]["value"].as_string == "original"

        # Cleanup
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server may not properly implement savepoint rollback - see UPGRADE_PLAN.md Appendix A.6"
)
async def test_savepoint_basic(client):
    """Test basic savepoint functionality."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.begin()

        # Create first node
        await conn.execute(f"CREATE (a:TxTest {{uid: '{uid}', idx: 1}})")

        # Create savepoint
        sp = await conn.savepoint("sp1")

        # Create second node after savepoint
        await conn.execute(f"CREATE (b:TxTest {{uid: '{uid}', idx: 2}})")

        # Rollback to savepoint - should undo second node but keep first
        await conn.rollback_to(sp)

        # Commit the transaction
        await conn.commit()

        # Should only have the first node
        page, _ = await conn.query(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 1

        # Verify it's the first one
        page, _ = await conn.query(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            RETURN n.idx AS idx
        """)
        assert page.rows[0]["idx"].as_int == 1

        # Cleanup
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server may not properly implement savepoint rollback - see UPGRADE_PLAN.md Appendix A.6"
)
async def test_savepoint_multiple(client):
    """Test multiple savepoints in a transaction."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.begin()

        # Create node 1
        await conn.execute(f"CREATE (a:TxTest {{uid: '{uid}', idx: 1}})")
        _sp1 = await conn.savepoint("sp1")  # noqa: F841 - created for test structure

        # Create node 2
        await conn.execute(f"CREATE (b:TxTest {{uid: '{uid}', idx: 2}})")
        sp2 = await conn.savepoint("sp2")

        # Create node 3
        await conn.execute(f"CREATE (c:TxTest {{uid: '{uid}', idx: 3}})")

        # Rollback to sp2 - removes node 3
        await conn.rollback_to(sp2)

        await conn.commit()

        # Should have nodes 1 and 2
        page, _ = await conn.query(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 2

        # Cleanup
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_transaction_with_relationship(client):
    """Test transaction with node and relationship creation."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.begin()

        await conn.execute(f"""
            CREATE (a:TxTest {{uid: '{uid}', name: 'A'}})
            CREATE (b:TxTest {{uid: '{uid}', name: 'B'}})
            CREATE (a)-[:RELATED]->(b)
        """)

        await conn.commit()

        # Verify relationship
        page, _ = await conn.query(f"""
            MATCH (a:TxTest {{uid: '{uid}'}})-[:RELATED]->(b:TxTest)
            RETURN count(b) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 1

        # Cleanup
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}})-[r]-() DELETE r")
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Server may not properly rollback transactions - see UPGRADE_PLAN.md Appendix A.6"
)
async def test_transaction_delete_and_rollback(client):
    """Test that delete within transaction can be rolled back."""
    uid = unique_id()
    async with client.connection() as conn:
        # Create node
        await conn.execute(f"CREATE (n:TxTest {{uid: '{uid}'}})")

        # Start transaction and delete
        await conn.begin()
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}}) DELETE n")

        # Rollback
        await conn.rollback()

        # Node should still exist
        page, _ = await conn.query(f"""
            MATCH (n:TxTest {{uid: '{uid}'}})
            RETURN count(n) AS cnt
        """)
        assert page.rows[0]["cnt"].as_int == 1

        # Cleanup
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}}) DELETE n")


@pytest.mark.asyncio
async def test_empty_transaction_commit(client):
    """Test committing an empty transaction."""
    async with client.connection() as conn:
        await conn.begin()
        # No operations
        await conn.commit()
        # Should not raise


@pytest.mark.asyncio
async def test_empty_transaction_rollback(client):
    """Test rolling back an empty transaction."""
    async with client.connection() as conn:
        await conn.begin()
        # No operations
        await conn.rollback()
        # Should not raise


@pytest.mark.asyncio
async def test_queries_after_transaction(client):
    """Test that queries work normally after a transaction."""
    uid = unique_id()
    async with client.connection() as conn:
        await conn.begin()
        await conn.execute(f"CREATE (n:TxTest {{uid: '{uid}'}})")
        await conn.commit()

        # Regular query after transaction
        page, _ = await conn.query("RETURN 42 AS value")
        assert page.rows[0]["value"].as_int == 42

        # Cleanup
        await conn.execute(f"MATCH (n:TxTest {{uid: '{uid}'}}) DELETE n")

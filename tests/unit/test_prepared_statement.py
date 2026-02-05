"""
Unit tests for PreparedStatement and related features.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from geode_client import (
    BatchResult,
    GeodeError,
    Page,
    PlanOperation,
    PreparedStatement,
    QueryError,
    QueryPlan,
    QueryProfile,
)


class TestPreparedStatement:
    """Tests for PreparedStatement class."""

    def test_extract_parameters_simple(self):
        """Extract single parameter from query."""
        params = PreparedStatement.extract_parameters("MATCH (n {id: $id}) RETURN n")
        assert params == ["id"]

    def test_extract_parameters_multiple(self):
        """Extract multiple parameters from query."""
        params = PreparedStatement.extract_parameters(
            "MATCH (n {id: $id, name: $name}) WHERE n.age > $min_age RETURN n"
        )
        assert params == ["id", "name", "min_age"]

    def test_extract_parameters_duplicates(self):
        """Duplicate parameters should appear once."""
        params = PreparedStatement.extract_parameters(
            "MATCH (a {id: $id})-[:KNOWS]->(b {id: $id}) RETURN a, b"
        )
        assert params == ["id"]

    def test_extract_parameters_none(self):
        """Query without parameters should return empty list."""
        params = PreparedStatement.extract_parameters("MATCH (n:Person) RETURN n")
        assert params == []

    def test_extract_parameters_underscore(self):
        """Parameters with underscores should be extracted."""
        params = PreparedStatement.extract_parameters(
            "MATCH (n {user_id: $user_id, first_name: $first_name}) RETURN n"
        )
        assert params == ["user_id", "first_name"]

    def test_extract_parameters_in_string_literal(self):
        """Parameters in string literals are still extracted (simplistic regex)."""
        # Note: This is a limitation - in production you'd want proper parsing
        params = PreparedStatement.extract_parameters(
            "RETURN '$not_a_param' AS x, $real_param AS y"
        )
        # The simple regex will find both - this is expected behavior
        assert "real_param" in params

    def test_properties(self):
        """Test PreparedStatement property accessors."""
        conn = MagicMock()
        stmt = PreparedStatement(
            connection=conn,
            query="MATCH (n {id: $id}) RETURN n",
            statement_id="test-123",
            parameters=["id"],
        )

        assert stmt.query == "MATCH (n {id: $id}) RETURN n"
        assert stmt.statement_id == "test-123"
        assert stmt.parameters == ["id"]
        assert stmt.closed is False

    def test_parameters_returns_copy(self):
        """Parameters property should return a copy."""
        conn = MagicMock()
        stmt = PreparedStatement(
            connection=conn,
            query="MATCH (n {id: $id}) RETURN n",
            statement_id="test-123",
            parameters=["id", "name"],
        )

        params = stmt.parameters
        params.append("extra")
        assert stmt.parameters == ["id", "name"]

    @pytest.mark.asyncio
    async def test_execute_calls_connection_query(self):
        """Execute should call connection.query with proper args."""
        conn = AsyncMock()
        mock_page = Page(columns=[], rows=[], final=True)
        conn.query.return_value = (mock_page, AsyncMock())

        stmt = PreparedStatement(
            connection=conn,
            query="MATCH (n {id: $id}) RETURN n",
            statement_id="test-123",
            parameters=["id"],
        )

        page, pager = await stmt.execute({"id": 1})

        conn.query.assert_called_once_with(
            "MATCH (n {id: $id}) RETURN n", {"id": 1}, None
        )
        assert page == mock_page

    @pytest.mark.asyncio
    async def test_execute_with_page_size(self):
        """Execute should pass page_size to connection.query."""
        conn = AsyncMock()
        mock_page = Page(columns=[], rows=[], final=True)
        conn.query.return_value = (mock_page, AsyncMock())

        stmt = PreparedStatement(
            connection=conn,
            query="MATCH (n) RETURN n",
            statement_id="test-123",
            parameters=[],
        )

        await stmt.execute(page_size=500)

        conn.query.assert_called_once_with("MATCH (n) RETURN n", None, 500)

    @pytest.mark.asyncio
    async def test_execute_after_close_raises(self):
        """Execute should raise if statement is closed."""
        conn = AsyncMock()
        stmt = PreparedStatement(
            connection=conn,
            query="MATCH (n) RETURN n",
            statement_id="test-123",
            parameters=[],
        )

        await stmt.close()

        with pytest.raises(GeodeError, match="Statement is closed"):
            await stmt.execute()

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        """Calling close multiple times should not raise."""
        conn = AsyncMock()
        stmt = PreparedStatement(
            connection=conn,
            query="MATCH (n) RETURN n",
            statement_id="test-123",
            parameters=[],
        )

        await stmt.close()
        await stmt.close()  # Should not raise

        assert stmt.closed is True

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """PreparedStatement should work as async context manager."""
        conn = AsyncMock()
        mock_page = Page(columns=[], rows=[], final=True)
        conn.query.return_value = (mock_page, AsyncMock())

        stmt = PreparedStatement(
            connection=conn,
            query="MATCH (n) RETURN n",
            statement_id="test-123",
            parameters=[],
        )

        async with stmt:
            assert stmt.closed is False
            await stmt.execute()

        assert stmt.closed is True


class TestQueryPlan:
    """Tests for QueryPlan dataclass."""

    def test_basic_creation(self):
        """Test basic QueryPlan creation."""
        plan = QueryPlan(
            query="MATCH (n) RETURN n",
            estimated_total_cost=1.5,
            planning_time_ms=0.5,
        )

        assert plan.query == "MATCH (n) RETURN n"
        assert plan.root is None
        assert plan.estimated_total_cost == 1.5
        assert plan.planning_time_ms == 0.5

    def test_with_operations(self):
        """Test QueryPlan with operation tree."""
        scan_op = PlanOperation(
            operation="NodeScan",
            description="Scan all nodes",
            estimated_rows=100,
            estimated_cost=1.0,
        )
        filter_op = PlanOperation(
            operation="Filter",
            description="Filter by label",
            estimated_rows=50,
            estimated_cost=0.5,
            children=[scan_op],
        )

        plan = QueryPlan(
            query="MATCH (n:Person) RETURN n",
            root=filter_op,
            estimated_total_cost=1.5,
        )

        assert plan.root is not None
        assert plan.root.operation == "Filter"
        assert len(plan.root.children) == 1
        assert plan.root.children[0].operation == "NodeScan"


class TestPlanOperation:
    """Tests for PlanOperation dataclass."""

    def test_basic_creation(self):
        """Test basic PlanOperation creation."""
        op = PlanOperation(
            operation="NodeScan",
            description="Scan all nodes",
            estimated_rows=1000,
            estimated_cost=5.0,
        )

        assert op.operation == "NodeScan"
        assert op.description == "Scan all nodes"
        assert op.estimated_rows == 1000
        assert op.estimated_cost == 5.0
        assert op.children == []

    def test_children_default(self):
        """Children should default to empty list."""
        op = PlanOperation(operation="Test", description="Test op")
        assert op.children == []

    def test_nested_operations(self):
        """Test nested operation tree."""
        leaf = PlanOperation(operation="Leaf", description="Leaf node")
        middle = PlanOperation(
            operation="Middle",
            description="Middle node",
            children=[leaf],
        )
        root = PlanOperation(
            operation="Root",
            description="Root node",
            children=[middle],
        )

        assert len(root.children) == 1
        assert root.children[0].operation == "Middle"
        assert root.children[0].children[0].operation == "Leaf"


class TestQueryProfile:
    """Tests for QueryProfile dataclass."""

    def test_basic_creation(self):
        """Test basic QueryProfile creation."""
        profile = QueryProfile(
            query="MATCH (n) RETURN n",
            execution_time_ms=10.5,
            planning_time_ms=1.2,
            rows_returned=100,
            rows_scanned=1000,
        )

        assert profile.query == "MATCH (n) RETURN n"
        assert profile.execution_time_ms == 10.5
        assert profile.planning_time_ms == 1.2
        assert profile.rows_returned == 100
        assert profile.rows_scanned == 1000
        assert profile.operations == []

    def test_operations_default(self):
        """Operations should default to empty list."""
        profile = QueryProfile(query="RETURN 1")
        assert profile.operations == []

    def test_with_operations(self):
        """Test profile with operation details."""
        profile = QueryProfile(
            query="MATCH (n) RETURN n",
            execution_time_ms=10.0,
            operations=[
                {"name": "NodeScan", "actual_rows": 100, "time_ms": 8.0},
                {"name": "Return", "actual_rows": 100, "time_ms": 2.0},
            ],
        )

        assert len(profile.operations) == 2
        assert profile.operations[0]["name"] == "NodeScan"


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_success_result(self):
        """Test successful batch result."""
        page = Page(columns=[], rows=[], final=True)
        result = BatchResult(
            index=0,
            success=True,
            page=page,
            error=None,
        )

        assert result.index == 0
        assert result.success is True
        assert result.page is page
        assert result.error is None

    def test_error_result(self):
        """Test failed batch result."""
        result = BatchResult(
            index=1,
            success=False,
            page=None,
            error="Query failed: syntax error",
        )

        assert result.index == 1
        assert result.success is False
        assert result.page is None
        assert result.error == "Query failed: syntax error"


class TestConnectionPrepare:
    """Tests for Connection.prepare() method."""

    @pytest.mark.asyncio
    async def test_prepare_extracts_parameters(self):
        """Prepare should extract parameters from query."""
        from geode_client.client import Connection

        conn = Connection(host="localhost", port=3141)
        # We don't actually connect - just test the prepare logic

        with patch.object(conn, "_connected", True):
            stmt = await conn.prepare("MATCH (n {id: $id, name: $name}) RETURN n")

            assert stmt.parameters == ["id", "name"]
            assert stmt.query == "MATCH (n {id: $id, name: $name}) RETURN n"
            assert stmt.statement_id  # Should have an ID

    @pytest.mark.asyncio
    async def test_prepare_no_parameters(self):
        """Prepare should handle queries without parameters."""
        from geode_client.client import Connection

        conn = Connection(host="localhost", port=3141)

        with patch.object(conn, "_connected", True):
            stmt = await conn.prepare("MATCH (n:Person) RETURN n")

            assert stmt.parameters == []


class TestConnectionBatch:
    """Tests for Connection.batch() method."""

    @pytest.mark.asyncio
    async def test_batch_executes_all_queries(self):
        """Batch should execute all queries and return results."""
        from geode_client.client import Connection

        conn = Connection(host="localhost", port=3141)
        conn._connected = True

        # Mock query method
        call_count = 0

        async def mock_query(text, params, page_size=None):
            nonlocal call_count
            call_count += 1
            return Page(columns=[], rows=[], final=True), AsyncMock()

        conn.query = mock_query

        queries = [
            ("CREATE (n:Person {name: 'Alice'})", None),
            ("CREATE (n:Person {name: 'Bob'})", None),
            ("MATCH (n:Person) RETURN count(n)", None),
        ]

        results = await conn.batch(queries)

        assert call_count == 3
        assert len(results) == 3
        assert all(r.success for r in results)
        assert [r.index for r in results] == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_batch_stops_on_error(self):
        """Batch should stop on first error when stop_on_error=True."""
        from geode_client.client import Connection

        conn = Connection(host="localhost", port=3141)
        conn._connected = True

        call_count = 0

        async def mock_query(text, params, page_size=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise QueryError("Syntax error")
            return Page(columns=[], rows=[], final=True), AsyncMock()

        conn.query = mock_query

        queries = [
            ("QUERY 1", None),
            ("QUERY 2 - will fail", None),
            ("QUERY 3 - skipped", None),
        ]

        results = await conn.batch(queries, stop_on_error=True)

        assert call_count == 2  # Third query not executed
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert "Syntax error" in results[1].error
        assert results[2].success is False
        assert "Skipped" in results[2].error

    @pytest.mark.asyncio
    async def test_batch_continues_on_error(self):
        """Batch should continue after error when stop_on_error=False."""
        from geode_client.client import Connection

        conn = Connection(host="localhost", port=3141)
        conn._connected = True

        call_count = 0

        async def mock_query(text, params, page_size=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise QueryError("Syntax error")
            return Page(columns=[], rows=[], final=True), AsyncMock()

        conn.query = mock_query

        queries = [
            ("QUERY 1", None),
            ("QUERY 2 - will fail", None),
            ("QUERY 3 - still runs", None),
        ]

        results = await conn.batch(queries, stop_on_error=False)

        assert call_count == 3  # All queries attempted
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True

    @pytest.mark.asyncio
    async def test_batch_with_parameters(self):
        """Batch should pass parameters to queries."""
        from geode_client.client import Connection

        conn = Connection(host="localhost", port=3141)
        conn._connected = True

        captured_params = []

        async def mock_query(text, params, page_size=None):
            captured_params.append(params)
            return Page(columns=[], rows=[], final=True), AsyncMock()

        conn.query = mock_query

        queries = [
            ("CREATE (n:Person {name: $name})", {"name": "Alice"}),
            ("CREATE (n:Person {name: $name})", {"name": "Bob"}),
        ]

        await conn.batch(queries)

        assert captured_params == [{"name": "Alice"}, {"name": "Bob"}]

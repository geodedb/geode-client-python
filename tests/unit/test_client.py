"""Unit tests for the client module."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from geode_client.client import (
    AuthError,
    BatchResult,
    Client,
    Column,
    Connection,
    GeodeConnectionError,
    GeodeError,
    GeodeProtocol,
    MAX_LINE_SIZE,
    Page,
    PlanOperation,
    PreparedStatement,
    QueryError,
    QueryPlan,
    QueryProfile,
    Savepoint,
    StreamReader,
    StreamWriter,
    open_database,
)


class TestDataclasses:
    """Test client dataclasses."""

    def test_savepoint_creation(self):
        """Test Savepoint dataclass creation."""
        sp = Savepoint(name="sp1", connection=None)
        assert sp.name == "sp1"
        assert sp.connection is None

    def test_column_creation(self):
        """Test Column dataclass creation."""
        col = Column(name="id", type="INT64")
        assert col.name == "id"
        assert col.type == "INT64"

    def test_page_creation(self):
        """Test Page dataclass creation."""
        columns = [Column(name="n", type="NODE")]
        rows = [{"n": {"id": 1}}]
        page = Page(columns=columns, rows=rows, ordered=True, final=True)
        assert len(page.columns) == 1
        assert len(page.rows) == 1
        assert page.ordered is True
        assert page.final is True

    def test_page_default_values(self):
        """Test Page default values."""
        page = Page(columns=[], rows=[])
        assert page.ordered is False
        assert page.order_keys == []
        assert page.final is False

    def test_plan_operation_creation(self):
        """Test PlanOperation dataclass creation."""
        op = PlanOperation(
            operation="NodeScan",
            description="Scan all Person nodes",
            estimated_rows=100,
            estimated_cost=1.5,
        )
        assert op.operation == "NodeScan"
        assert op.estimated_rows == 100
        assert op.estimated_cost == 1.5
        assert op.children == []

    def test_plan_operation_with_children(self):
        """Test PlanOperation with children."""
        child = PlanOperation(operation="Filter", description="Filter by age")
        parent = PlanOperation(
            operation="NodeScan",
            description="Scan",
            children=[child],
        )
        assert len(parent.children) == 1
        assert parent.children[0].operation == "Filter"

    def test_query_plan_creation(self):
        """Test QueryPlan dataclass creation."""
        plan = QueryPlan(
            query="MATCH (n) RETURN n",
            estimated_total_cost=2.5,
            planning_time_ms=0.5,
        )
        assert plan.query == "MATCH (n) RETURN n"
        assert plan.root is None
        assert plan.estimated_total_cost == 2.5
        assert plan.planning_time_ms == 0.5

    def test_query_profile_creation(self):
        """Test QueryProfile dataclass creation."""
        profile = QueryProfile(
            query="MATCH (n) RETURN n",
            execution_time_ms=1.5,
            planning_time_ms=0.2,
            rows_returned=10,
            rows_scanned=100,
        )
        assert profile.query == "MATCH (n) RETURN n"
        assert profile.execution_time_ms == 1.5
        assert profile.rows_returned == 10
        assert profile.rows_scanned == 100
        assert profile.operations == []

    def test_batch_result_creation(self):
        """Test BatchResult dataclass creation."""
        result = BatchResult(index=0, success=True, page=None, error=None)
        assert result.index == 0
        assert result.success is True

    def test_batch_result_with_error(self):
        """Test BatchResult with error."""
        result = BatchResult(index=1, success=False, page=None, error="Query failed")
        assert result.success is False
        assert result.error == "Query failed"


class TestExceptions:
    """Test exception classes."""

    def test_geode_error(self):
        """Test GeodeError base exception."""
        error = GeodeError("test error")
        assert str(error) == "test error"

    def test_geode_connection_error(self):
        """Test GeodeConnectionError."""
        error = GeodeConnectionError("connection failed")
        assert str(error) == "connection failed"
        assert isinstance(error, GeodeError)

    def test_query_error(self):
        """Test QueryError."""
        error = QueryError("query failed")
        assert str(error) == "query failed"
        assert isinstance(error, GeodeError)

    def test_auth_error(self):
        """Test AuthError."""
        error = AuthError("auth failed")
        assert str(error) == "auth failed"
        assert isinstance(error, GeodeError)


class TestStreamReader:
    """Test StreamReader class."""

    @pytest.mark.asyncio
    async def test_read_from_queue(self):
        """Test reading from the queue."""
        queue = asyncio.Queue()
        reader = StreamReader(queue)

        queue.put_nowait(b"hello")
        data = await reader.read()
        assert data == b"hello"

    @pytest.mark.asyncio
    async def test_read_with_limit(self):
        """Test reading with a byte limit."""
        queue = asyncio.Queue()
        reader = StreamReader(queue)

        queue.put_nowait(b"hello world")
        data = await reader.read(5)
        assert data == b"hello"

        # Read remaining from buffer
        data = await reader.read(6)
        assert data == b" world"

    @pytest.mark.asyncio
    async def test_read_buffered_data(self):
        """Test reading buffered data."""
        queue = asyncio.Queue()
        reader = StreamReader(queue)
        reader._buffer = b"buffered"

        data = await reader.read()
        assert data == b"buffered"
        assert reader._buffer == b""

    @pytest.mark.asyncio
    async def test_read_buffered_with_limit(self):
        """Test reading buffered data with limit."""
        queue = asyncio.Queue()
        reader = StreamReader(queue)
        reader._buffer = b"buffered data"

        data = await reader.read(8)
        assert data == b"buffered"
        assert reader._buffer == b" data"

    @pytest.mark.asyncio
    async def test_read_end_of_stream(self):
        """Test reading end of stream (None)."""
        queue = asyncio.Queue()
        reader = StreamReader(queue)

        queue.put_nowait(None)
        data = await reader.read()
        assert data == b""


class TestStreamWriter:
    """Test StreamWriter class."""

    def test_write(self):
        """Test write method."""
        mock_protocol = MagicMock()
        writer = StreamWriter(mock_protocol, stream_id=1)

        writer.write(b"hello")
        mock_protocol.write_to_stream.assert_called_once_with(1, b"hello")

    @pytest.mark.asyncio
    async def test_drain(self):
        """Test drain method (should just yield control)."""
        mock_protocol = MagicMock()
        writer = StreamWriter(mock_protocol, stream_id=1)

        await writer.drain()  # Should not raise

    def test_close(self):
        """Test close method."""
        mock_protocol = MagicMock()
        writer = StreamWriter(mock_protocol, stream_id=1)

        writer.close()
        mock_protocol.close_stream.assert_called_once_with(1)


class TestPreparedStatement:
    """Test PreparedStatement class."""

    def test_init(self):
        """Test PreparedStatement initialization."""
        mock_conn = MagicMock()
        stmt = PreparedStatement(
            connection=mock_conn,
            query="MATCH (n) RETURN n",
            statement_id="stmt-1",
            parameters=["name"],
        )
        assert stmt.query == "MATCH (n) RETURN n"
        assert stmt.statement_id == "stmt-1"
        assert stmt.parameters == ["name"]
        assert stmt.closed is False

    @pytest.mark.asyncio
    async def test_execute(self):
        """Test execute method."""
        mock_conn = MagicMock()
        mock_conn.query = AsyncMock(return_value=(MagicMock(), lambda: None))

        stmt = PreparedStatement(
            connection=mock_conn,
            query="MATCH (n {name: $name}) RETURN n",
            statement_id="stmt-1",
            parameters=["name"],
        )

        page, pager = await stmt.execute({"name": "Alice"})
        mock_conn.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_closed_statement(self):
        """Test executing a closed statement raises error."""
        mock_conn = MagicMock()
        stmt = PreparedStatement(
            connection=mock_conn,
            query="MATCH (n) RETURN n",
            statement_id="stmt-1",
            parameters=[],
        )
        stmt._closed = True

        with pytest.raises(GeodeError, match="Statement is closed"):
            await stmt.execute()

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        mock_conn = MagicMock()
        stmt = PreparedStatement(
            connection=mock_conn,
            query="MATCH (n) RETURN n",
            statement_id="stmt-1",
            parameters=[],
        )

        await stmt.close()
        assert stmt.closed is True

    @pytest.mark.asyncio
    async def test_close_already_closed(self):
        """Test closing already closed statement is no-op."""
        mock_conn = MagicMock()
        stmt = PreparedStatement(
            connection=mock_conn,
            query="MATCH (n) RETURN n",
            statement_id="stmt-1",
            parameters=[],
        )
        stmt._closed = True

        await stmt.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        mock_conn = MagicMock()
        stmt = PreparedStatement(
            connection=mock_conn,
            query="MATCH (n) RETURN n",
            statement_id="stmt-1",
            parameters=[],
        )

        async with stmt as s:
            assert s is stmt
            assert s.closed is False

        assert stmt.closed is True

    def test_extract_parameters(self):
        """Test extracting parameters from query."""
        params = PreparedStatement.extract_parameters(
            "MATCH (n {id: $id, name: $name}) WHERE n.age > $min_age RETURN n"
        )
        assert params == ["id", "name", "min_age"]

    def test_extract_parameters_duplicates(self):
        """Test extracting parameters removes duplicates."""
        params = PreparedStatement.extract_parameters(
            "MATCH (n {name: $name}) WHERE n.name = $name RETURN n"
        )
        assert params == ["name"]

    def test_extract_parameters_no_params(self):
        """Test extracting from query with no parameters."""
        params = PreparedStatement.extract_parameters("MATCH (n) RETURN n")
        assert params == []


class TestConnection:
    """Test Connection class."""

    def test_init_defaults(self):
        """Test Connection default initialization."""
        conn = Connection()
        assert conn.host == "127.0.0.1"
        assert conn.port == 3141
        assert conn.page_size == 1000
        assert conn._connected is False

    def test_init_localhost_normalized(self):
        """Test localhost is normalized to 127.0.0.1."""
        conn = Connection(host="localhost")
        assert conn.host == "127.0.0.1"

    def test_init_custom_params(self):
        """Test Connection with custom parameters."""
        conn = Connection(
            host="192.168.1.1",
            port=8443,
            page_size=500,
            hello_name="test-client",
            hello_ver="1.0.0",
            conformance="full",
            skip_verify=True,
            server_name="geode.example.com",
        )
        assert conn.host == "192.168.1.1"
        assert conn.port == 8443
        assert conn.page_size == 500
        assert conn.skip_verify is True

    def test_parse_rows(self):
        """Test _parse_rows method."""
        conn = Connection()
        type_map = {"name": "STRING", "age": "INT64"}
        raw_rows = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

        rows = conn._parse_rows(raw_rows, type_map)
        assert len(rows) == 2
        assert rows[0]["name"].str_value == "Alice"
        assert rows[1]["age"].int_value == 25


class TestConnectionTransaction:
    """Test Connection transaction methods with mocked I/O."""

    @pytest.fixture
    def mock_connection(self):
        """Create a connection with mocked internal methods."""
        conn = Connection()
        conn._lock = asyncio.Lock()
        conn._write_json = AsyncMock()
        conn._read_json = AsyncMock(return_value={"status": "00000"})
        return conn

    @pytest.mark.asyncio
    async def test_begin(self, mock_connection):
        """Test begin transaction."""
        await mock_connection.begin()

        mock_connection._write_json.assert_called_once_with({"type": "BEGIN"})
        mock_connection._read_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit(self, mock_connection):
        """Test commit transaction."""
        await mock_connection.commit()

        mock_connection._write_json.assert_called_once_with({"type": "COMMIT"})
        mock_connection._read_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback(self, mock_connection):
        """Test rollback transaction."""
        await mock_connection.rollback()

        mock_connection._write_json.assert_called_once_with({"type": "ROLLBACK"})
        mock_connection._read_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_savepoint(self, mock_connection):
        """Test create savepoint."""
        sp = await mock_connection.savepoint("sp1")

        assert sp.name == "sp1"
        assert sp.connection is mock_connection
        mock_connection._write_json.assert_called_once_with(
            {"type": "SAVEPOINT", "name": "sp1"}
        )

    @pytest.mark.asyncio
    async def test_rollback_to(self, mock_connection):
        """Test rollback to savepoint."""
        sp = Savepoint(name="sp1", connection=mock_connection)
        await mock_connection.rollback_to(sp)

        mock_connection._write_json.assert_called_once_with(
            {"type": "ROLLBACK_TO", "name": "sp1"}
        )

    @pytest.mark.asyncio
    async def test_savepoint_validates_name(self, mock_connection):
        """Test that savepoint name is validated as identifier."""
        from geode_client.validate import ValidationError

        # Invalid names should raise ValidationError
        with pytest.raises(ValidationError, match="Invalid identifier"):
            await mock_connection.savepoint("1invalid")  # starts with digit

        with pytest.raises(ValidationError, match="Invalid identifier"):
            await mock_connection.savepoint("invalid-name")  # contains hyphen

        with pytest.raises(ValidationError, match="cannot be empty"):
            await mock_connection.savepoint("")  # empty

    @pytest.mark.asyncio
    async def test_rollback_to_validates_name(self, mock_connection):
        """Test that rollback_to validates savepoint name."""
        from geode_client.validate import ValidationError

        # Even with manually created Savepoint, validation should occur
        bad_sp = Savepoint(name="invalid-name", connection=mock_connection)
        with pytest.raises(ValidationError, match="Invalid identifier"):
            await mock_connection.rollback_to(bad_sp)


class TestConnectionIO:
    """Test Connection I/O methods."""

    @pytest.mark.asyncio
    async def test_write_json_not_connected(self):
        """Test _write_json raises when not connected."""
        conn = Connection()
        conn._writer = None

        with pytest.raises(GeodeConnectionError, match="Not connected"):
            await conn._write_json({"type": "TEST"})

    @pytest.mark.asyncio
    async def test_read_line_not_connected(self):
        """Test _read_line raises when not connected."""
        conn = Connection()
        conn._reader = None

        with pytest.raises(GeodeConnectionError, match="Not connected"):
            await conn._read_line()

    @pytest.mark.asyncio
    async def test_read_line_from_buffer(self):
        """Test _read_line when data is in buffer."""
        conn = Connection()
        mock_reader = MagicMock()
        conn._reader = mock_reader
        conn._buffer = b"line one\nline two\n"

        line = await conn._read_line()
        assert line == b"line one"
        assert conn._buffer == b"line two\n"

    @pytest.mark.asyncio
    async def test_read_line_stream_closed(self):
        """Test _read_line when stream is closed."""
        conn = Connection()
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"")
        conn._reader = mock_reader
        conn._buffer = b""

        with pytest.raises(GeodeConnectionError, match="Stream closed"):
            await conn._read_line()

    @pytest.mark.asyncio
    async def test_read_line_partial_buffer(self):
        """Test _read_line with partial line in buffer."""
        conn = Connection()
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(return_value=b"ello\n")
        conn._reader = mock_reader
        conn._buffer = b"h"

        line = await conn._read_line()
        assert line == b"hello"


class TestConnectionClose:
    """Test Connection close method."""

    @pytest.mark.asyncio
    async def test_close_not_connected(self):
        """Test close when not connected."""
        conn = Connection()
        conn._connected = False

        await conn.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_with_writer(self):
        """Test close cleans up writer."""
        conn = Connection()
        conn._connected = True
        conn._writer = MagicMock()

        await conn.close()

        assert conn._connected is False
        assert conn._writer is None
        assert conn._reader is None


class TestConnectionQuery:
    """Test Connection query method."""

    @pytest.fixture
    def mock_connection_for_query(self):
        """Create a connection with mocked I/O for query tests."""
        conn = Connection()
        conn._lock = asyncio.Lock()
        conn._write_json = AsyncMock()
        conn._read_json = AsyncMock()
        return conn

    @pytest.mark.asyncio
    async def test_query_error_response(self, mock_connection_for_query):
        """Test query with error response."""
        conn = mock_connection_for_query
        conn._read_json.return_value = {
            "result": {
                "type": "ERROR",
                "code": "SYNTAX_ERROR",
                "message": "Invalid syntax",
            }
        }

        with pytest.raises(QueryError, match="SYNTAX_ERROR"):
            await conn.query("INVALID QUERY")

    @pytest.mark.asyncio
    async def test_query_unexpected_frame(self, mock_connection_for_query):
        """Test query with unexpected frame type."""
        conn = mock_connection_for_query
        conn._read_json.return_value = {
            "result": {"type": "UNKNOWN"}
        }

        with pytest.raises(QueryError, match="Unexpected frame type"):
            await conn.query("MATCH (n) RETURN n")

    @pytest.mark.asyncio
    async def test_query_result_type(self, mock_connection_for_query):
        """Test query with RESULT type response."""
        conn = mock_connection_for_query
        conn._read_json.side_effect = [
            # SCHEMA response
            {
                "result": {
                    "type": "SCHEMA",
                    "columns": [{"name": "n", "type": "INT64"}],
                }
            },
            # RESULT response (complete result)
            {
                "result": {
                    "type": "RESULT",
                    "rows": [{"n": 1}, {"n": 2}],
                    "ordered": True,
                }
            },
        ]

        page, pager = await conn.query("RETURN 1")
        assert len(page.rows) == 2
        assert page.final is True

    @pytest.mark.asyncio
    async def test_query_bindings_type(self, mock_connection_for_query):
        """Test query with BINDINGS type response."""
        conn = mock_connection_for_query
        conn._read_json.side_effect = [
            # SCHEMA response
            {
                "result": {
                    "type": "SCHEMA",
                    "columns": [{"name": "n", "type": "STRING"}],
                }
            },
            # BINDINGS response
            {
                "result": {
                    "type": "BINDINGS",
                    "rows": [{"n": "Alice"}],
                    "ordered": False,
                    "final": True,
                }
            },
        ]

        page, pager = await conn.query("MATCH (n) RETURN n.name AS n")
        assert len(page.rows) == 1
        assert page.final is True

    @pytest.mark.asyncio
    async def test_query_profile_type(self, mock_connection_for_query):
        """Test query with PROFILE type response."""
        conn = mock_connection_for_query
        conn._read_json.side_effect = [
            # SCHEMA response
            {
                "result": {
                    "type": "SCHEMA",
                    "columns": [],
                }
            },
            # PROFILE response
            {
                "result": {
                    "type": "PROFILE",
                }
            },
        ]

        page, pager = await conn.query("MATCH (n) RETURN n")
        assert len(page.rows) == 0
        assert page.final is True

    @pytest.mark.asyncio
    async def test_query_bindings_not_final(self, mock_connection_for_query):
        """Test query with BINDINGS that are not final (pagination)."""
        conn = mock_connection_for_query
        conn._read_json.side_effect = [
            # SCHEMA response
            {
                "result": {
                    "type": "SCHEMA",
                    "columns": [{"name": "n", "type": "INT64"}],
                }
            },
            # BINDINGS response (not final)
            {
                "result": {
                    "type": "BINDINGS",
                    "rows": [{"n": 1}],
                    "ordered": False,
                    "final": False,
                }
            },
        ]

        page, pager = await conn.query("MATCH (n) RETURN n")
        assert page.final is False
        # Pager function should be callable
        assert callable(pager)


class TestConnectionExplain:
    """Test Connection explain method."""

    @pytest.fixture
    def mock_connection_for_explain(self):
        """Create a connection with mocked I/O for explain tests."""
        conn = Connection()
        conn._lock = asyncio.Lock()
        conn._write_json = AsyncMock()
        conn._read_json = AsyncMock()
        return conn

    @pytest.mark.asyncio
    async def test_explain_success(self, mock_connection_for_explain):
        """Test explain with successful response."""
        conn = mock_connection_for_explain
        conn._read_json.return_value = {
            "result": {
                "type": "EXPLAIN",
                "plan": {
                    "operation": "NodeScan",
                    "description": "Scan Person nodes",
                    "estimated_rows": 100,
                    "estimated_cost": 1.5,
                    "children": [],
                },
                "estimated_total_cost": 1.5,
                "planning_time_ms": 0.2,
            }
        }

        plan = await conn.explain("MATCH (n:Person) RETURN n")

        assert plan.query == "MATCH (n:Person) RETURN n"
        assert plan.root is not None
        assert plan.root.operation == "NodeScan"
        assert plan.estimated_total_cost == 1.5

    @pytest.mark.asyncio
    async def test_explain_error(self, mock_connection_for_explain):
        """Test explain with error response."""
        conn = mock_connection_for_explain
        conn._read_json.return_value = {
            "result": {
                "type": "ERROR",
                "code": "SYNTAX_ERROR",
                "message": "Invalid query",
            }
        }

        with pytest.raises(QueryError, match="SYNTAX_ERROR"):
            await conn.explain("INVALID QUERY")

    @pytest.mark.asyncio
    async def test_explain_with_params(self, mock_connection_for_explain):
        """Test explain with parameters."""
        conn = mock_connection_for_explain
        conn._read_json.return_value = {
            "result": {
                "type": "EXPLAIN",
                "plan": {},
                "estimated_total_cost": 0.5,
                "planning_time_ms": 0.1,
            }
        }

        plan = await conn.explain(
            "MATCH (n {name: $name}) RETURN n",
            params={"name": "Alice"},
        )

        call_args = conn._write_json.call_args[0][0]
        assert call_args["params"] == {"name": "Alice"}


class TestConnectionProfile:
    """Test Connection profile method."""

    @pytest.fixture
    def mock_connection_for_profile(self):
        """Create a connection with mocked I/O for profile tests."""
        conn = Connection()
        conn._lock = asyncio.Lock()
        conn._write_json = AsyncMock()
        conn._read_json = AsyncMock()
        return conn

    @pytest.mark.asyncio
    async def test_profile_success(self, mock_connection_for_profile):
        """Test profile with successful response."""
        conn = mock_connection_for_profile
        conn._read_json.return_value = {
            "result": {
                "type": "PROFILE",
                "execution_time_ms": 5.2,
                "planning_time_ms": 0.3,
                "rows_returned": 10,
                "rows_scanned": 100,
                "operations": [{"op": "scan"}],
            }
        }

        profile = await conn.profile("MATCH (n) RETURN n")

        assert profile.query == "MATCH (n) RETURN n"
        assert profile.execution_time_ms == 5.2
        assert profile.rows_returned == 10
        assert profile.rows_scanned == 100

    @pytest.mark.asyncio
    async def test_profile_error(self, mock_connection_for_profile):
        """Test profile with error response."""
        conn = mock_connection_for_profile
        conn._read_json.return_value = {
            "result": {
                "type": "ERROR",
                "code": "PROFILE_ERROR",
                "message": "Cannot profile",
            }
        }

        with pytest.raises(QueryError, match="PROFILE_ERROR"):
            await conn.profile("MATCH (n) RETURN n")

    @pytest.mark.asyncio
    async def test_profile_with_params(self, mock_connection_for_profile):
        """Test profile with parameters."""
        conn = mock_connection_for_profile
        conn._read_json.return_value = {
            "result": {
                "type": "PROFILE",
                "execution_time_ms": 1.0,
            }
        }

        profile = await conn.profile(
            "MATCH (n {name: $name}) RETURN n",
            params={"name": "Alice"},
        )

        call_args = conn._write_json.call_args[0][0]
        assert call_args["params"] == {"name": "Alice"}


class TestConnectionBatch:
    """Test Connection batch method."""

    @pytest.fixture
    def mock_connection_for_batch(self):
        """Create a connection with mocked query method."""
        conn = Connection()
        conn.query = AsyncMock()
        return conn

    @pytest.mark.asyncio
    async def test_batch_success(self, mock_connection_for_batch):
        """Test batch with all successful queries."""
        conn = mock_connection_for_batch
        mock_page = Page(columns=[], rows=[], final=True)
        conn.query.return_value = (mock_page, lambda: None)

        results = await conn.batch([
            ("CREATE (n:Person)", None),
            ("CREATE (n:Company)", None),
        ])

        assert len(results) == 2
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_batch_with_error_stop(self, mock_connection_for_batch):
        """Test batch stops on error when stop_on_error=True."""
        conn = mock_connection_for_batch
        mock_page = Page(columns=[], rows=[], final=True)
        conn.query.side_effect = [
            (mock_page, lambda: None),
            QueryError("Second query failed"),
        ]

        results = await conn.batch([
            ("CREATE (n:Person)", None),
            ("INVALID QUERY", None),
            ("CREATE (n:Company)", None),
        ], stop_on_error=True)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert "Second query failed" in results[1].error
        assert results[2].success is False
        assert "Skipped" in results[2].error

    @pytest.mark.asyncio
    async def test_batch_continue_on_error(self, mock_connection_for_batch):
        """Test batch continues on error when stop_on_error=False."""
        conn = mock_connection_for_batch
        mock_page = Page(columns=[], rows=[], final=True)
        conn.query.side_effect = [
            (mock_page, lambda: None),
            QueryError("Second query failed"),
            (mock_page, lambda: None),
        ]

        results = await conn.batch([
            ("CREATE (n:Person)", None),
            ("INVALID QUERY", None),
            ("CREATE (n:Company)", None),
        ], stop_on_error=False)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True


class TestConnectionPrepare:
    """Test Connection prepare method."""

    @pytest.mark.asyncio
    async def test_prepare(self):
        """Test preparing a statement."""
        conn = Connection()

        stmt = await conn.prepare("MATCH (n {name: $name}) RETURN n")

        assert stmt.query == "MATCH (n {name: $name}) RETURN n"
        assert stmt.parameters == ["name"]
        assert stmt.statement_id is not None


class TestConnectionExecute:
    """Test Connection execute method."""

    @pytest.mark.asyncio
    async def test_execute(self):
        """Test execute method calls query."""
        conn = Connection()
        conn.query = AsyncMock(return_value=(Page(columns=[], rows=[]), lambda: None))

        await conn.execute("CREATE (n:Person)", {"name": "Alice"})

        conn.query.assert_called_once_with("CREATE (n:Person)", {"name": "Alice"}, page_size=0)


class TestClient:
    """Test Client class."""

    def test_init_defaults(self):
        """Test Client default initialization."""
        client = Client()
        assert client.host == "127.0.0.1"
        assert client.port == 3141

    def test_init_custom(self):
        """Test Client with custom parameters."""
        client = Client(host="192.168.1.1", port=8443, skip_verify=True)
        assert client.host == "192.168.1.1"
        assert client.port == 8443
        assert client.config["skip_verify"] is True

    def test_from_url_basic(self):
        """Test creating Client from basic URL."""
        client = Client.from_url("quic://localhost:3141")
        assert client.host == "localhost"
        assert client.port == 3141

    def test_from_url_with_params(self):
        """Test creating Client from URL with parameters."""
        client = Client.from_url(
            "quic://localhost:8443?page_size=500&skip_verify=true&hello_name=test"
        )
        assert client.port == 8443
        assert client.config["page_size"] == 500
        assert client.config["skip_verify"] is True
        assert client.config["hello_name"] == "test"

    def test_from_url_all_params(self):
        """Test creating Client from URL with all parameters."""
        client = Client.from_url(
            "quic://example.com:3141?"
            "page_size=100&"
            "hello_name=test&"
            "hello_ver=2.0&"
            "conformance=full&"
            "ca_cert=/path/to/ca.crt&"
            "client_cert=/path/to/cert.crt&"
            "client_key=/path/to/key.pem&"
            "skip_verify=1&"
            "server_name=custom.example.com"
        )
        assert client.host == "example.com"
        assert client.config["page_size"] == 100
        assert client.config["hello_ver"] == "2.0"
        assert client.config["conformance"] == "full"
        assert client.config["ca_cert"] == "/path/to/ca.crt"
        assert client.config["server_name"] == "custom.example.com"

    def test_from_url_defaults(self):
        """Test creating Client from URL uses defaults."""
        client = Client.from_url("quic://")
        assert client.host == "127.0.0.1"
        assert client.port == 3141

    def test_connection_factory(self):
        """Test connection() returns a Connection."""
        client = Client(host="192.168.1.1", port=8443)
        conn = client.connection()

        assert isinstance(conn, Connection)
        assert conn.host == "192.168.1.1"
        assert conn.port == 8443


class TestOpenDatabase:
    """Test open_database function."""

    def test_open_database(self):
        """Test open_database creates a Client."""
        client = open_database("quic://localhost:3141")
        assert isinstance(client, Client)
        assert client.host == "localhost"
        assert client.port == 3141

    def test_open_database_with_options(self):
        """Test open_database with URL options."""
        client = open_database("quic://localhost:3141?skip_verify=true")
        assert client.config.get("skip_verify") is True


class TestConnectionContextManager:
    """Test Connection async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_entry_exit(self):
        """Test connection context manager calls connect/close."""
        conn = Connection()
        conn.connect = AsyncMock()
        conn.close = AsyncMock()

        async with conn as c:
            assert c is conn
            conn.connect.assert_called_once()

        conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exception(self):
        """Test context manager closes on exception."""
        conn = Connection()
        conn.connect = AsyncMock()
        conn.close = AsyncMock()

        with pytest.raises(ValueError):
            async with conn:
                raise ValueError("test error")

        conn.close.assert_called_once()


class TestConnectionQueryPager:
    """Test Connection query pager functionality."""

    @pytest.fixture
    def mock_connection_for_pager(self):
        """Create a connection with mocked I/O for pager tests."""
        conn = Connection()
        conn._lock = asyncio.Lock()
        conn._write_json = AsyncMock()
        conn._read_json = AsyncMock()
        return conn

    @pytest.mark.asyncio
    async def test_pager_iteration(self, mock_connection_for_pager):
        """Test iterating through pager."""
        conn = mock_connection_for_pager
        conn._read_json.side_effect = [
            # SCHEMA response
            {
                "result": {
                    "type": "SCHEMA",
                    "columns": [{"name": "n", "type": "INT64"}],
                }
            },
            # BINDINGS response (not final)
            {
                "result": {
                    "type": "BINDINGS",
                    "rows": [{"n": 1}],
                    "ordered": False,
                    "final": False,
                }
            },
            # Second BINDINGS response (final)
            {
                "result": {
                    "type": "BINDINGS",
                    "rows": [{"n": 2}],
                    "ordered": False,
                    "final": True,
                }
            },
        ]

        page, pager = await conn.query("MATCH (n) RETURN n")
        assert page.final is False

        # Get next page
        pages = []
        async for p in pager():
            pages.append(p)

        assert len(pages) == 1
        assert pages[0].final is True

    @pytest.mark.asyncio
    async def test_pager_error_stops(self, mock_connection_for_pager):
        """Test pager stops on error."""
        conn = mock_connection_for_pager
        conn._read_json.side_effect = [
            # SCHEMA response
            {
                "result": {
                    "type": "SCHEMA",
                    "columns": [{"name": "n", "type": "INT64"}],
                }
            },
            # BINDINGS response (not final)
            {
                "result": {
                    "type": "BINDINGS",
                    "rows": [{"n": 1}],
                    "ordered": False,
                    "final": False,
                }
            },
            # Error response
            {
                "result": {
                    "type": "ERROR",
                    "message": "Server error",
                }
            },
        ]

        page, pager = await conn.query("MATCH (n) RETURN n")

        pages = []
        async for p in pager():
            pages.append(p)

        # Pager should stop on error
        assert len(pages) == 0


class TestConnectionReadJson:
    """Test Connection _read_json method."""

    @pytest.mark.asyncio
    async def test_read_json_empty_line(self):
        """Test _read_json with empty line returns empty dict."""
        conn = Connection()
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(return_value=b"\n")
        conn._reader = mock_reader
        conn._buffer = b""

        result = await conn._read_json()
        assert result == {}


class TestConnectionWriteJson:
    """Test Connection _write_json method."""

    @pytest.mark.asyncio
    async def test_write_json_formats_correctly(self):
        """Test _write_json formats JSON with newline."""
        conn = Connection()
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()
        conn._writer = mock_writer

        await conn._write_json({"type": "TEST", "value": 123})

        written = mock_writer.write.call_args[0][0]
        assert b'"type": "TEST"' in written or b'"type":"TEST"' in written
        assert written.endswith(b"\n")


class TestGeodeProtocol:
    """Test GeodeProtocol class methods that can be tested without QUIC."""

    def test_close_stream(self):
        """Test close_stream removes stream from readers."""
        # Create a minimal protocol mock
        protocol = MagicMock(spec=GeodeProtocol)
        protocol._stream_readers = {1: asyncio.Queue(), 2: asyncio.Queue()}

        # Call the actual close_stream method
        GeodeProtocol.close_stream(protocol, 1)

        assert 1 not in protocol._stream_readers
        assert 2 in protocol._stream_readers

    def test_close_stream_not_found(self):
        """Test close_stream with unknown stream ID is no-op."""
        protocol = MagicMock(spec=GeodeProtocol)
        protocol._stream_readers = {}

        # Should not raise
        GeodeProtocol.close_stream(protocol, 999)


class TestBufferLimits:
    """Test buffer size limits to prevent DoS (SEC-026)."""

    def test_max_line_size_constant(self):
        """Test MAX_LINE_SIZE constant is defined and reasonable."""
        # Should be 16MB
        assert MAX_LINE_SIZE == 16 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_read_line_within_limit(self):
        """Test _read_line works for data within size limit."""
        conn = Connection(host="localhost", port=8443)
        conn._buffer = b""

        # Create mock reader that returns data with newline
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"test data\n")
        conn._reader = mock_reader

        line = await conn._read_line()
        assert line == b"test data"

    @pytest.mark.asyncio
    async def test_read_line_exceeds_limit(self):
        """Test _read_line raises error when buffer exceeds MAX_LINE_SIZE."""
        conn = Connection(host="localhost", port=8443)
        # Pre-fill buffer to exceed limit
        conn._buffer = b"x" * (MAX_LINE_SIZE + 1)

        # Create mock reader (won't be used since buffer already exceeds limit)
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"more data")
        conn._reader = mock_reader

        with pytest.raises(GeodeConnectionError) as exc_info:
            await conn._read_line()

        assert "exceeds maximum size" in str(exc_info.value)
        # Buffer should be cleared for recovery
        assert conn._buffer == b""

    @pytest.mark.asyncio
    async def test_read_line_gradual_growth_exceeds_limit(self):
        """Test _read_line raises error when gradual reads exceed limit."""
        conn = Connection(host="localhost", port=8443)
        conn._buffer = b""

        # Create mock reader that returns chunks without newline
        # Each read adds 4096 bytes (default chunk size)
        chunk_count = 0
        chunks_to_exceed = (MAX_LINE_SIZE // 4096) + 2

        async def mock_read(size):
            nonlocal chunk_count
            chunk_count += 1
            if chunk_count <= chunks_to_exceed:
                return b"x" * 4096  # No newline, keeps growing
            return b""  # End of stream

        mock_reader = AsyncMock()
        mock_reader.read = mock_read
        conn._reader = mock_reader

        with pytest.raises(GeodeConnectionError) as exc_info:
            await conn._read_line()

        assert "exceeds maximum size" in str(exc_info.value)

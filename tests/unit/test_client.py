"""Unit tests for the client module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from geode_client.client import (
    AuthError,
    BatchResult,
    Client,
    Column,
    Connection,
    GeodeConnectionError,
    GeodeError,
    Page,
    PlanOperation,
    PreparedStatement,
    QueryError,
    QueryPlan,
    QueryProfile,
    Savepoint,
    open_database,
)
from geode_client.transport import TransportType


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

    def test_init_with_transport_type(self):
        """Test Connection with transport type."""
        conn = Connection(transport_type=TransportType.GRPC)
        assert conn.transport_type == TransportType.GRPC


class TestConnectionTransport:
    """Test Connection with mocked transport."""

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.session_id = "sess_123"
        transport.connect = AsyncMock()
        transport.close = AsyncMock()
        transport.hello = AsyncMock()
        transport.execute = AsyncMock()
        transport.pull = AsyncMock()
        transport.ping = AsyncMock(return_value=True)
        transport.begin = AsyncMock()
        transport.commit = AsyncMock()
        transport.rollback = AsyncMock()
        return transport

    @pytest.fixture
    def mock_hello_response(self):
        """Create a mock successful hello response."""
        response = MagicMock()
        response.success = True
        response.session_id = "sess_123"
        response.error_message = ""
        return response

    @pytest.mark.asyncio
    async def test_begin_calls_transport(self, mock_transport):
        """Test begin() calls transport.begin()."""
        conn = Connection()
        conn._transport = mock_transport
        conn._connected = True

        mock_response = MagicMock()
        mock_response.HasField = MagicMock(return_value=True)
        mock_transport.begin.return_value = mock_response

        await conn.begin()

        mock_transport.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_calls_transport(self, mock_transport):
        """Test commit() calls transport.commit()."""
        conn = Connection()
        conn._transport = mock_transport
        conn._connected = True

        mock_response = MagicMock()
        mock_response.HasField = MagicMock(return_value=True)
        mock_transport.commit.return_value = mock_response

        await conn.commit()

        mock_transport.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_calls_transport(self, mock_transport):
        """Test rollback() calls transport.rollback()."""
        conn = Connection()
        conn._transport = mock_transport
        conn._connected = True

        mock_response = MagicMock()
        mock_response.HasField = MagicMock(return_value=True)
        mock_transport.rollback.return_value = mock_response

        await conn.rollback()

        mock_transport.rollback.assert_called_once()


class TestSavepointInjection:
    """Test that savepoint/rollback_to prevent GQL injection."""

    @pytest.fixture
    def connected_conn(self):
        """Create a connected Connection with mocked transport."""
        conn = Connection()
        transport = MagicMock()
        transport.session_id = "sess_123"
        transport.execute = AsyncMock()
        transport.read_next = AsyncMock()
        # Mock execute response for savepoint (no-result statement)
        response = MagicMock()
        response.HasField = MagicMock(
            side_effect=lambda f: f == "execute"
        )
        exec_resp = MagicMock()
        exec_resp.HasField = MagicMock(return_value=False)
        exec_resp.schema.columns = []
        data_page = MagicMock()
        data_page.rows = []
        data_page.final = True
        exec_resp.pages = [data_page]
        response.execute = exec_resp
        transport.execute.return_value = response
        conn._transport = transport
        conn._connected = True
        return conn

    def test_savepoint_valid_name_passes_validation(self):
        """Test savepoint with valid identifier name passes validation."""
        from geode_client.validate import identifier

        # Should not raise
        result = identifier("sp1")
        assert result == "sp1"
        result = identifier("my_savepoint_2")
        assert result == "my_savepoint_2"

    @pytest.mark.asyncio
    async def test_savepoint_rejects_injection(self, connected_conn):
        """Test savepoint rejects GQL injection in name."""
        from geode_client.validate import ValidationError

        with pytest.raises(ValidationError):
            await connected_conn.savepoint("x; DELETE (n) DETACH; SAVEPOINT y")

    @pytest.mark.asyncio
    async def test_savepoint_rejects_semicolon(self, connected_conn):
        """Test savepoint rejects semicolons."""
        from geode_client.validate import ValidationError

        with pytest.raises(ValidationError):
            await connected_conn.savepoint("sp1; DROP DATABASE")

    @pytest.mark.asyncio
    async def test_savepoint_rejects_spaces(self, connected_conn):
        """Test savepoint rejects names with spaces."""
        from geode_client.validate import ValidationError

        with pytest.raises(ValidationError):
            await connected_conn.savepoint("sp 1")

    @pytest.mark.asyncio
    async def test_rollback_to_rejects_injection(self, connected_conn):
        """Test rollback_to rejects GQL injection in savepoint name."""
        from geode_client.validate import ValidationError

        evil_sp = Savepoint(
            name="x; MATCH (n) DELETE n DETACH; ROLLBACK TO SAVEPOINT y",
            connection=connected_conn,
        )
        with pytest.raises(ValidationError):
            await connected_conn.rollback_to(evil_sp)

    def test_rollback_to_valid_name_passes_validation(self):
        """Test rollback_to with valid savepoint name passes validation."""
        from geode_client.validate import identifier

        # Should not raise - valid names for rollback_to
        result = identifier("valid_savepoint")
        assert result == "valid_savepoint"


class TestConnectionClose:
    """Test Connection close method."""

    @pytest.mark.asyncio
    async def test_close_not_connected(self):
        """Test close when not connected."""
        conn = Connection()
        conn._connected = False

        await conn.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_with_transport(self):
        """Test close cleans up transport."""
        conn = Connection()
        conn._connected = True
        mock_transport = MagicMock()
        mock_transport.close = AsyncMock()
        conn._transport = mock_transport

        await conn.close()

        assert conn._connected is False
        assert conn._transport is None
        mock_transport.close.assert_called_once()


class TestClient:
    """Test Client class."""

    def test_init_defaults(self):
        """Test Client default initialization."""
        client = Client()
        assert client.host == "127.0.0.1"
        assert client.port == 3141

    def test_init_custom_params(self):
        """Test Client with custom parameters."""
        client = Client(host="192.168.1.1", port=8443, skip_verify=True)
        assert client.host == "192.168.1.1"
        assert client.port == 8443
        assert client.config["skip_verify"] is True

    def test_from_url_quic(self):
        """Test Client.from_url with QUIC scheme."""
        client = Client.from_url("quic://localhost:3141")
        # localhost is normalized to 127.0.0.1
        assert client.host == "127.0.0.1"
        assert client.port == 3141
        assert client.transport_type == TransportType.QUIC

    def test_from_url_grpc(self):
        """Test Client.from_url with gRPC scheme."""
        client = Client.from_url("grpc://localhost:50051")
        assert client.host == "127.0.0.1"
        assert client.port == 50051
        assert client.transport_type == TransportType.GRPC

    def test_from_url_with_params(self):
        """Test Client.from_url with query parameters."""
        client = Client.from_url("quic://localhost:3141?skip_verify=1&page_size=500")
        assert client.config["skip_verify"] is True
        assert client.config["page_size"] == 500

    def test_connection_returns_connection_object(self):
        """Test connection() returns a Connection object."""
        client = Client(host="localhost", port=3141)
        conn = client.connection()
        assert isinstance(conn, Connection)
        assert conn.host == "127.0.0.1"
        assert conn.port == 3141


class TestOpenDatabase:
    """Test open_database function."""

    def test_open_database_quic(self):
        """Test open_database with QUIC URL."""
        client = open_database("quic://localhost:3141")
        assert isinstance(client, Client)
        assert client.host == "127.0.0.1"
        assert client.transport_type == TransportType.QUIC

    def test_open_database_grpc(self):
        """Test open_database with gRPC URL."""
        client = open_database("grpc://localhost:50051")
        assert isinstance(client, Client)
        assert client.transport_type == TransportType.GRPC

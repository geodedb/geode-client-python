"""Unit tests for the client module."""

import warnings
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

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
    SecurityWarning,
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
        response.HasField = MagicMock(side_effect=lambda f: f == "execute")
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


class TestConnectionConnect:
    """Test Connection.connect() method."""

    @pytest.mark.asyncio
    async def test_connect_skip_verify_emits_warning(self):
        """Test connect() emits SecurityWarning when skip_verify=True."""
        conn = Connection(skip_verify=True)

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock()
        mock_transport.hello = AsyncMock()
        mock_transport.session_id = "sess_1"

        # Make hello succeed
        hello_resp = MagicMock()
        hello_resp.success = True
        hello_resp.session_id = "sess_1"
        mock_transport.hello.return_value = hello_resp

        with patch("geode_client.client.create_transport", return_value=mock_transport):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                await conn.connect()
                sec_warnings = [x for x in w if issubclass(x.category, SecurityWarning)]
                assert len(sec_warnings) >= 1
                assert "skip_verify" in str(sec_warnings[0].message)

        await conn.close()

    @pytest.mark.asyncio
    async def test_connect_already_connected_noop(self):
        """Test connect() is no-op when already connected."""
        conn = Connection()
        conn._connected = True
        # Should not raise or do anything
        await conn.connect()

    @pytest.mark.asyncio
    async def test_connect_transport_failure(self):
        """Test connect() raises GeodeConnectionError on transport failure."""
        conn = Connection()

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock(side_effect=Exception("boom"))

        with patch("geode_client.client.create_transport", return_value=mock_transport):
            with pytest.raises(GeodeConnectionError, match="Failed to connect"):
                await conn.connect()

    @pytest.mark.asyncio
    async def test_connect_hello_fails(self):
        """Test connect() raises AuthError on failed handshake."""
        conn = Connection()

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock()
        hello_resp = MagicMock()
        hello_resp.success = False
        hello_resp.error_message = "bad credentials"
        mock_transport.hello = AsyncMock(return_value=hello_resp)

        with patch("geode_client.client.create_transport", return_value=mock_transport):
            with pytest.raises(AuthError, match="Authentication failed"):
                await conn.connect()

    @pytest.mark.asyncio
    async def test_connect_hello_timeout(self):
        """Test connect() handles timeout during hello."""
        import asyncio

        conn = Connection()

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock()
        mock_transport.hello = AsyncMock(side_effect=asyncio.TimeoutError)

        with patch("geode_client.client.create_transport", return_value=mock_transport):
            with pytest.raises(GeodeConnectionError, match="Timeout"):
                await conn.connect()

    @pytest.mark.asyncio
    async def test_connect_transport_error_during_hello(self):
        """Test connect() handles TransportError during hello."""
        from geode_client.transport import TransportError

        conn = Connection()

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock()
        mock_transport.hello = AsyncMock(side_effect=TransportError("proto error"))

        with patch("geode_client.client.create_transport", return_value=mock_transport):
            with pytest.raises(GeodeConnectionError, match="Handshake failed"):
                await conn.connect()


class TestConnectionQuery:
    """Test Connection.query() and related methods with mocked transport."""

    @pytest.fixture
    def connected_conn(self):
        """Create a connected Connection with mocked transport."""
        conn = Connection()
        transport = MagicMock()
        transport.session_id = "sess_123"
        transport.execute = AsyncMock()
        transport.pull = AsyncMock()
        transport.read_next = AsyncMock()
        conn._transport = transport
        conn._connected = True
        return conn

    def _make_exec_response(self, columns=None, rows=None, final=True, has_page=True):
        """Create a mock execute response."""
        resp = MagicMock()
        resp.HasField = MagicMock(
            side_effect=lambda f: {
                "execute": True,
                "error": False,
                "schema": columns is not None,
                "page": has_page,
            }.get(f, False)
        )

        exec_resp = MagicMock()
        exec_resp.HasField = MagicMock(
            side_effect=lambda f: {
                "error": False,
                "schema": columns is not None,
                "page": has_page,
            }.get(f, False)
        )

        if columns:
            schema_cols = []
            for name, type_name in columns:
                col = MagicMock()
                col.name = name
                col.type = type_name
                schema_cols.append(col)
            exec_resp.schema.columns = schema_cols

        if has_page:
            page = MagicMock()
            page.ordered = False
            page.order_keys = []
            page.final = final
            page.rows = rows or []
            exec_resp.page = page

        resp.execute = exec_resp
        return resp

    @pytest.mark.asyncio
    async def test_query_not_execute_response(self, connected_conn):
        """Test query raises QueryError when response is not execute."""
        resp = MagicMock()
        resp.HasField = MagicMock(return_value=False)
        connected_conn._transport.execute.return_value = resp

        with pytest.raises(QueryError, match="Expected Execute response"):
            await connected_conn.query("RETURN 1")

    @pytest.mark.asyncio
    async def test_query_with_error_response(self, connected_conn):
        """Test query raises QueryError on server error."""
        resp = MagicMock()
        resp.HasField = MagicMock(side_effect=lambda f: f == "execute")
        exec_resp = MagicMock()
        exec_resp.HasField = MagicMock(side_effect=lambda f: f == "error")
        exec_resp.error.code = "SYNTAX"
        exec_resp.error.message = "bad query"
        resp.execute = exec_resp
        connected_conn._transport.execute.return_value = resp

        with pytest.raises(QueryError, match="SYNTAX.*bad query"):
            await connected_conn.query("BAD QUERY")

    @pytest.mark.asyncio
    async def test_query_treats_no_data_error_as_empty_result(self, connected_conn):
        """Test 02000/no-data responses become empty pages."""
        resp = MagicMock()
        resp.HasField = MagicMock(side_effect=lambda f: f == "execute")
        exec_resp = MagicMock()
        exec_resp.HasField = MagicMock(side_effect=lambda f: f == "error")
        exec_resp.error.code = "02000"
        exec_resp.error.message = "No active result set"
        resp.execute = exec_resp
        connected_conn._transport.execute.return_value = resp

        page, pager = await connected_conn.query("MATCH (n:Missing) RETURN n")
        assert page.final is True
        assert page.rows == []
        assert page.columns == []
        assert pager == connected_conn._empty_pager

    @pytest.mark.asyncio
    async def test_query_empty_result(self, connected_conn):
        """Test query returns empty page when no schema/page."""
        resp = MagicMock()
        resp.HasField = MagicMock(side_effect=lambda f: f == "execute")
        exec_resp = MagicMock()
        exec_resp.HasField = MagicMock(return_value=False)
        resp.execute = exec_resp
        # Remove read_next so it falls through to empty result path
        del connected_conn._transport.read_next
        connected_conn._transport.execute.return_value = resp

        page, pager = await connected_conn.query("RETURN 1")
        assert page.final is True
        assert page.rows == []

    @pytest.mark.asyncio
    async def test_query_with_final_page(self, connected_conn):
        """Test query returns final page without pager."""
        resp = self._make_exec_response(
            columns=[("x", "INT")],
            rows=[],
            final=True,
        )
        connected_conn._transport.execute.return_value = resp

        page, pager = await connected_conn.query("RETURN 1 AS x")
        assert page.final is True


class TestProtoValueConversion:
    """Test _proto_value_to_python conversion paths."""

    def _make_conn(self):
        conn = Connection()
        return conn

    def test_null_value(self):
        """Test converting null proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "null_val")
        result = conn._proto_value_to_python(proto, "NULL")
        assert result.kind.name == "NULL"

    def test_int_value(self):
        """Test converting int proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "int_val")
        proto.int_val.value = 42
        result = conn._proto_value_to_python(proto, "INT")
        assert result.as_int == 42

    def test_bool_value(self):
        """Test converting bool proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "bool_val")
        proto.bool_val = True
        result = conn._proto_value_to_python(proto, "BOOL")
        assert result.as_bool is True

    def test_double_value(self):
        """Test converting double proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "double_val")
        proto.double_val.value = 3.14
        result = conn._proto_value_to_python(proto, "DECIMAL")
        assert result.as_decimal == Decimal("3.14")

    def test_string_value(self):
        """Test converting string proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "string_val")
        proto.string_val.value = "hello"
        result = conn._proto_value_to_python(proto, "STRING")
        assert result.as_string == "hello"

    def test_bytes_value(self):
        """Test converting bytes proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "bytes_val")
        proto.bytes_val.value = b"\x01\x02"
        result = conn._proto_value_to_python(proto, "BYTEA")
        assert result.as_bytes == b"\x01\x02"

    def test_list_value(self):
        """Test converting list proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "list_val")
        # Inner value: int
        inner = MagicMock()
        inner.HasField = MagicMock(side_effect=lambda f: f == "int_val")
        inner.int_val.value = 1
        proto.list_val.values = [inner]
        result = conn._proto_value_to_python(proto, "ARRAY")
        assert result.kind.name == "ARRAY"
        assert len(result.as_array) == 1

    def test_map_value(self):
        """Test converting map proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "map_val")
        entry = MagicMock()
        entry.key = "name"
        inner_val = MagicMock()
        inner_val.HasField = MagicMock(side_effect=lambda f: f == "string_val")
        inner_val.string_val.value = "Alice"
        entry.value = inner_val
        proto.map_val.entries = [entry]
        result = conn._proto_value_to_python(proto, "OBJECT")
        assert result.kind.name == "OBJECT"

    def test_node_value(self):
        """Test converting node proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "node_val")
        proto.node_val.id = 1
        proto.node_val.labels = ["Person"]
        proto.node_val.properties = []
        result = conn._proto_value_to_python(proto, "NODE")
        assert result.kind.name == "NODE"
        assert result.object_value["id"].as_int == 1

    def test_edge_value(self):
        """Test converting edge proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "edge_val")
        proto.edge_val.id = 10
        proto.edge_val.from_id = 1
        proto.edge_val.to_id = 2
        proto.edge_val.label = "KNOWS"
        proto.edge_val.properties = []
        result = conn._proto_value_to_python(proto, "EDGE")
        assert result.kind.name == "EDGE"
        assert result.object_value["type"].as_string == "KNOWS"

    def test_path_value(self):
        """Test converting path proto value."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "path_val")
        # Create a node
        node = MagicMock()
        node.id = 1
        node.labels = ["A"]
        node.properties = []
        # Create an edge
        edge = MagicMock()
        edge.id = 100
        edge.from_id = 1
        edge.to_id = 2
        edge.label = "REL"
        edge.properties = []
        proto.path_val.nodes = [node]
        proto.path_val.edges = [edge]
        result = conn._proto_value_to_python(proto, "PATH")
        assert result.kind.name == "PATH"
        assert "nodes" in result.object_value
        assert "edges" in result.object_value

    def test_ext_value_text(self):
        """Test converting ext value with text."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "ext_val")
        proto.ext_val.HasField = MagicMock(side_effect=lambda f: f == "text")
        proto.ext_val.text = "extended text"
        result = conn._proto_value_to_python(proto, "EXT")
        assert result.as_string == "extended text"

    def test_ext_value_int(self):
        """Test converting ext value with int."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "ext_val")
        proto.ext_val.HasField = MagicMock(side_effect=lambda f: f == "int_val")
        proto.ext_val.int_val = 99
        result = conn._proto_value_to_python(proto, "EXT")
        assert result.as_int == 99

    def test_ext_value_double(self):
        """Test converting ext value with double."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "ext_val")
        proto.ext_val.HasField = MagicMock(side_effect=lambda f: f == "double_val")
        proto.ext_val.double_val = 1.5
        result = conn._proto_value_to_python(proto, "EXT")
        assert result.as_decimal == Decimal("1.5")

    def test_ext_value_bool(self):
        """Test converting ext value with bool."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "ext_val")
        proto.ext_val.HasField = MagicMock(side_effect=lambda f: f == "bool_val")
        proto.ext_val.bool_val = False
        result = conn._proto_value_to_python(proto, "EXT")
        assert result.as_bool is False

    def test_ext_value_bytes(self):
        """Test converting ext value with bytes."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "ext_val")
        proto.ext_val.HasField = MagicMock(side_effect=lambda f: f == "bytes")
        proto.ext_val.bytes = b"\xab\xcd"
        result = conn._proto_value_to_python(proto, "EXT")
        assert result.as_bytes == b"\xab\xcd"

    def test_ext_value_fallback(self):
        """Test converting ext value with unknown sub-type."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(side_effect=lambda f: f == "ext_val")
        proto.ext_val.HasField = MagicMock(return_value=False)
        proto.ext_val.type_name = "CUSTOM"
        result = conn._proto_value_to_python(proto, "EXT")
        assert result.as_string == "CUSTOM"

    def test_unknown_field_returns_null(self):
        """Test converting proto value with no recognized field returns NULL."""
        conn = self._make_conn()
        proto = MagicMock()
        proto.HasField = MagicMock(return_value=False)
        result = conn._proto_value_to_python(proto, "UNKNOWN")
        assert result.kind.name == "NULL"


class TestPythonToProtoConversion:
    """Test _python_to_proto_value conversion."""

    def test_none_value(self):
        conn = Connection()
        result = conn._python_to_proto_value(None)
        assert result.HasField("null_val")

    def test_bool_value(self):
        conn = Connection()
        result = conn._python_to_proto_value(True)
        assert result.bool_val is True

    def test_int_value(self):
        conn = Connection()
        result = conn._python_to_proto_value(42)
        assert result.int_val.value == 42

    def test_float_value(self):
        conn = Connection()
        result = conn._python_to_proto_value(3.14)
        assert result.double_val.value == 3.14

    def test_str_value(self):
        conn = Connection()
        result = conn._python_to_proto_value("hello")
        assert result.string_val.value == "hello"

    def test_fallback_to_string(self):
        """Test non-standard types are converted to string."""
        conn = Connection()
        result = conn._python_to_proto_value([1, 2, 3])
        assert result.string_val.value == "[1, 2, 3]"


class TestConnectionExplainAndProfile:
    """Test explain() and profile() methods."""

    @pytest.fixture
    def connected_conn(self):
        conn = Connection()
        transport = MagicMock()
        transport.session_id = "sess_123"
        transport.execute = AsyncMock()
        transport.read_next = AsyncMock()
        conn._transport = transport
        conn._connected = True
        return conn

    def _make_empty_response(self):
        resp = MagicMock()
        resp.HasField = MagicMock(side_effect=lambda f: f == "execute")
        exec_resp = MagicMock()
        exec_resp.HasField = MagicMock(side_effect=lambda f: f == "page")
        page = MagicMock()
        page.ordered = False
        page.order_keys = []
        page.final = True
        page.rows = []
        exec_resp.page = page
        exec_resp.schema.columns = []
        resp.execute = exec_resp
        return resp

    @pytest.mark.asyncio
    async def test_explain_returns_query_plan(self, connected_conn):
        """Test explain() returns a QueryPlan."""
        connected_conn._transport.execute.return_value = self._make_empty_response()
        plan = await connected_conn.explain("MATCH (n) RETURN n")
        assert isinstance(plan, QueryPlan)
        assert plan.query == "MATCH (n) RETURN n"

    @pytest.mark.asyncio
    async def test_profile_returns_query_profile(self, connected_conn):
        """Test profile() returns a QueryProfile."""
        connected_conn._transport.execute.return_value = self._make_empty_response()
        prof = await connected_conn.profile("MATCH (n) RETURN n")
        assert isinstance(prof, QueryProfile)
        assert prof.query == "MATCH (n) RETURN n"


class TestConnectionBatch:
    """Test batch() method."""

    @pytest.fixture
    def connected_conn(self):
        conn = Connection()
        transport = MagicMock()
        transport.session_id = "sess_123"
        transport.execute = AsyncMock()
        transport.read_next = AsyncMock()
        conn._transport = transport
        conn._connected = True
        return conn

    def _make_success_response(self):
        resp = MagicMock()
        resp.HasField = MagicMock(side_effect=lambda f: f == "execute")
        exec_resp = MagicMock()
        exec_resp.HasField = MagicMock(side_effect=lambda f: f == "page")
        page = MagicMock()
        page.ordered = False
        page.order_keys = []
        page.final = True
        page.rows = []
        exec_resp.page = page
        exec_resp.schema.columns = []
        resp.execute = exec_resp
        return resp

    def _make_error_response(self):
        resp = MagicMock()
        resp.HasField = MagicMock(side_effect=lambda f: f == "execute")
        exec_resp = MagicMock()
        exec_resp.HasField = MagicMock(side_effect=lambda f: f == "error")
        exec_resp.error.code = "ERR"
        exec_resp.error.message = "fail"
        resp.execute = exec_resp
        return resp

    @pytest.mark.asyncio
    async def test_batch_all_success(self, connected_conn):
        """Test batch with all queries succeeding."""
        connected_conn._transport.execute.return_value = self._make_success_response()
        results = await connected_conn.batch(
            [
                ("RETURN 1", None),
                ("RETURN 2", None),
            ]
        )
        assert len(results) == 2
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_batch_stop_on_error(self, connected_conn):
        """Test batch stops on error and marks remaining as skipped."""
        connected_conn._transport.execute.side_effect = [
            self._make_success_response(),
            self._make_error_response(),
        ]
        results = await connected_conn.batch(
            [
                ("RETURN 1", None),
                ("BAD QUERY", None),
                ("RETURN 3", None),
            ]
        )
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is False
        assert "Skipped" in results[2].error

    @pytest.mark.asyncio
    async def test_batch_continue_on_error(self, connected_conn):
        """Test batch continues on error with stop_on_error=False."""
        connected_conn._transport.execute.side_effect = [
            self._make_error_response(),
            self._make_success_response(),
        ]
        results = await connected_conn.batch(
            [("BAD", None), ("RETURN 1", None)],
            stop_on_error=False,
        )
        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is True


class TestConnectionPrepare:
    """Test prepare() method."""

    @pytest.mark.asyncio
    async def test_prepare_returns_statement(self):
        """Test prepare() returns a PreparedStatement."""
        conn = Connection()
        conn._transport = MagicMock()
        conn._connected = True
        stmt = await conn.prepare("MATCH (n {id: $id}) RETURN n")
        assert isinstance(stmt, PreparedStatement)
        assert stmt.query == "MATCH (n {id: $id}) RETURN n"
        assert "id" in stmt.parameters

    @pytest.mark.asyncio
    async def test_prepare_generates_unique_ids(self):
        """Test prepare() generates unique statement IDs."""
        conn = Connection()
        conn._transport = MagicMock()
        conn._connected = True
        stmt1 = await conn.prepare("RETURN 1")
        stmt2 = await conn.prepare("RETURN 2")
        assert stmt1.statement_id != stmt2.statement_id


class TestConnectionContextManager:
    """Test Connection as async context manager."""

    @pytest.mark.asyncio
    async def test_aenter_calls_connect(self):
        """Test __aenter__ calls connect()."""
        conn = Connection()
        with patch.object(conn, "connect", new_callable=AsyncMock) as mock_connect:
            with patch.object(conn, "close", new_callable=AsyncMock):
                async with conn as c:
                    assert c is conn
                    mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_aexit_calls_close(self):
        """Test __aexit__ calls close()."""
        conn = Connection()
        with patch.object(conn, "connect", new_callable=AsyncMock):
            with patch.object(conn, "close", new_callable=AsyncMock) as mock_close:
                async with conn:
                    pass
                mock_close.assert_called_once()


class TestClientConnect:
    """Test Client.connect() method."""

    @pytest.mark.asyncio
    async def test_connect_returns_connection(self):
        """Test Client.connect() returns a connected Connection."""
        client = Client(host="localhost", port=3141)

        mock_transport = MagicMock()
        mock_transport.connect = AsyncMock()
        mock_transport.session_id = "sess_1"
        hello_resp = MagicMock()
        hello_resp.success = True
        hello_resp.session_id = "sess_1"
        mock_transport.hello = AsyncMock(return_value=hello_resp)

        with patch("geode_client.client.create_transport", return_value=mock_transport):
            conn = await client.connect()
            assert isinstance(conn, Connection)
            assert conn._connected is True
            await conn.close()


class TestParseProtoRows:
    """Test _parse_proto_rows method."""

    def test_missing_values_default_to_null(self):
        """Test rows with fewer values than columns default to NULL."""
        conn = Connection()
        columns = [Column(name="a", type="INT"), Column(name="b", type="STRING")]
        proto_row = MagicMock()
        proto_row.values = []  # No values at all
        rows = conn._parse_proto_rows([proto_row], columns)
        assert len(rows) == 1
        assert rows[0]["a"].kind.name == "NULL"
        assert rows[0]["b"].kind.name == "NULL"

    def test_partial_values(self):
        """Test rows with some values fill remaining with NULL."""
        conn = Connection()
        columns = [Column(name="a", type="INT"), Column(name="b", type="STRING")]
        proto_val = MagicMock()
        proto_val.HasField = MagicMock(side_effect=lambda f: f == "int_val")
        proto_val.int_val.value = 5
        proto_row = MagicMock()
        proto_row.values = [proto_val]  # Only one value for two columns
        rows = conn._parse_proto_rows([proto_row], columns)
        assert rows[0]["a"].as_int == 5
        assert rows[0]["b"].kind.name == "NULL"


class TestConnectionExecute:
    """Test Connection.execute() method."""

    @pytest.mark.asyncio
    async def test_execute_calls_query(self):
        """Test execute() calls query() and discards results."""
        conn = Connection()
        conn._transport = MagicMock()
        conn._connected = True
        mock_page = Page(columns=[], rows=[], final=True)

        async def mock_empty():
            if False:
                yield

        with patch.object(
            conn, "query", new_callable=AsyncMock, return_value=(mock_page, mock_empty)
        ):
            await conn.execute("CREATE (n:Node)")
            conn.query.assert_called_once_with("CREATE (n:Node)", None, page_size=0)

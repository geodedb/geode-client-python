"""Unit tests for transport module - DSN parsing and transport selection."""

import asyncio
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from geode_client.transport import (
    MAX_MESSAGE_SIZE,
    GrpcTransport,
    QuicTransport,
    TransportConfig,
    TransportConnectionError,
    TransportError,
    TransportType,
    UnsupportedSchemeError,
    create_transport,
    parse_dsn,
)


class TestDsnParsing:
    """Test DSN parsing functionality."""

    def test_quic_basic(self):
        """Test parsing basic quic:// DSN."""
        config = parse_dsn("quic://localhost:1234")
        assert config.transport_type == TransportType.QUIC
        assert config.host == "127.0.0.1"  # localhost normalized
        assert config.port == 1234

    def test_quic_explicit_host(self):
        """Test parsing quic:// with explicit host."""
        config = parse_dsn("quic://192.168.1.1:3141")
        assert config.transport_type == TransportType.QUIC
        assert config.host == "192.168.1.1"
        assert config.port == 3141

    def test_quic_default_port(self):
        """Test quic:// uses default port 3141."""
        config = parse_dsn("quic://localhost")
        assert config.transport_type == TransportType.QUIC
        assert config.port == 3141

    def test_grpc_basic(self):
        """Test parsing basic grpc:// DSN."""
        config = parse_dsn("grpc://127.0.0.1:50051")
        assert config.transport_type == TransportType.GRPC
        assert config.host == "127.0.0.1"
        assert config.port == 50051

    def test_grpc_tls_disabled(self):
        """Test parsing grpc:// with TLS disabled."""
        config = parse_dsn("grpc://127.0.0.1:50051?tls=0")
        assert config.transport_type == TransportType.GRPC
        assert config.host == "127.0.0.1"
        assert config.port == 50051
        assert config.tls_enabled is False

    def test_grpc_default_port(self):
        """Test grpc:// uses default port 50051."""
        config = parse_dsn("grpc://localhost")
        assert config.transport_type == TransportType.GRPC
        assert config.port == 50051

    def test_grcp_scheme_rejected(self):
        """Test grcp:// scheme is rejected (no longer supported)."""
        with pytest.raises(UnsupportedSchemeError) as exc_info:
            parse_dsn("grcp://localhost:50051")
        assert exc_info.value.scheme == "grcp"

    def test_geode_scheme_rejected(self):
        """Test geode:// scheme is rejected (no longer supported)."""
        with pytest.raises(UnsupportedSchemeError) as exc_info:
            parse_dsn("geode://localhost:3141")
        assert exc_info.value.scheme == "geode"

    def test_ipv6_address(self):
        """Test parsing IPv6 address."""
        config = parse_dsn("grpc://[::1]:50051")
        assert config.host == "::1"
        assert config.port == 50051

    def test_ipv6_full_address(self):
        """Test parsing full IPv6 address."""
        config = parse_dsn("quic://[2001:db8::1]:3141")
        assert config.host == "2001:db8::1"
        assert config.port == 3141

    def test_query_params_tls(self):
        """Test parsing TLS query parameters."""
        config = parse_dsn("quic://localhost:3141?tls=1&skip_verify=1")
        assert config.tls_enabled is True
        assert config.skip_verify is True

    def test_query_params_auth(self):
        """Test parsing authentication query parameters."""
        config = parse_dsn("quic://localhost:3141?username=admin&password=secret")
        assert config.username == "admin"
        assert config.password == "secret"

    def test_query_params_auth_aliases(self):
        """Test parsing auth aliases (user, pass)."""
        config = parse_dsn("quic://localhost:3141?user=admin&pass=secret")
        assert config.username == "admin"
        assert config.password == "secret"

    def test_query_params_page_size(self):
        """Test parsing page_size query parameter."""
        config = parse_dsn("quic://localhost:3141?page_size=5000")
        assert config.page_size == 5000

    def test_query_params_certs(self):
        """Test parsing certificate paths."""
        config = parse_dsn(
            "quic://localhost:3141?"
            "ca_cert=/path/to/ca.crt&"
            "client_cert=/path/to/client.crt&"
            "client_key=/path/to/client.key"
        )
        assert config.ca_cert == "/path/to/ca.crt"
        assert config.client_cert == "/path/to/client.crt"
        assert config.client_key == "/path/to/client.key"

    def test_invalid_scheme_http(self):
        """Test that http:// scheme raises error."""
        with pytest.raises(UnsupportedSchemeError) as exc_info:
            parse_dsn("http://localhost:1")
        assert exc_info.value.scheme == "http"
        assert "http" in str(exc_info.value)

    def test_invalid_scheme_https(self):
        """Test that https:// scheme raises error."""
        with pytest.raises(UnsupportedSchemeError) as exc_info:
            parse_dsn("https://localhost:443")
        assert exc_info.value.scheme == "https"

    def test_invalid_scheme_tcp(self):
        """Test that tcp:// scheme raises error."""
        with pytest.raises(UnsupportedSchemeError) as exc_info:
            parse_dsn("tcp://localhost:1234")
        assert exc_info.value.scheme == "tcp"

    def test_empty_scheme_defaults_to_quic(self):
        """Test that missing scheme defaults to QUIC."""
        # Note: urlparse treats "localhost:3141" differently
        # This tests the case where scheme is explicitly empty
        config = parse_dsn("//localhost:3141")
        assert config.transport_type == TransportType.QUIC

    def test_localhost_normalized(self):
        """Test that localhost is normalized to 127.0.0.1."""
        config = parse_dsn("quic://localhost:3141")
        assert config.host == "127.0.0.1"


class TestTransportCreation:
    """Test transport factory function."""

    def test_create_quic_transport(self):
        """Test creating QUIC transport."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = create_transport(config)
        assert isinstance(transport, QuicTransport)

    def test_create_grpc_transport(self):
        """Test creating gRPC transport."""
        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="localhost",
            port=50051,
        )
        transport = create_transport(config)
        assert isinstance(transport, GrpcTransport)


class TestTransportConfig:
    """Test TransportConfig dataclass."""

    def test_default_values(self):
        """Test TransportConfig default values."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        assert config.tls_enabled is True
        assert config.skip_verify is False
        assert config.ca_cert is None
        assert config.username == ""
        assert config.password == ""
        assert config.page_size == 1000

    def test_all_fields(self):
        """Test TransportConfig with all fields set."""
        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="192.168.1.1",
            port=50051,
            tls_enabled=False,
            skip_verify=True,
            ca_cert="/path/to/ca.crt",
            client_cert="/path/to/client.crt",
            client_key="/path/to/client.key",
            server_name="geode.example.com",
            username="admin",
            password="secret",
            page_size=5000,
            hello_name="test-client",
            hello_ver="1.0.0",
            conformance="full",
        )
        assert config.transport_type == TransportType.GRPC
        assert config.host == "192.168.1.1"
        assert config.port == 50051
        assert config.tls_enabled is False
        assert config.skip_verify is True


class TestUnsupportedSchemeError:
    """Test UnsupportedSchemeError exception."""

    def test_error_message(self):
        """Test error message format."""
        error = UnsupportedSchemeError("http")
        assert error.scheme == "http"
        assert "http" in str(error)
        assert "quic://" in str(error)
        assert "grpc://" in str(error)

    def test_is_transport_error(self):
        """Test that UnsupportedSchemeError is a TransportError."""
        error = UnsupportedSchemeError("http")
        assert isinstance(error, TransportError)


class TestTransportConnectionError:
    """Test TransportConnectionError exception."""

    def test_error_message_format(self):
        """Test error message includes transport, host, port."""
        error = TransportConnectionError("failed", "quic", "localhost", 3141)
        assert "quic://localhost:3141" in str(error)
        assert "failed" in str(error)
        assert error.transport == "quic"
        assert error.host == "localhost"
        assert error.port == 3141

    def test_is_transport_error(self):
        """Test that TransportConnectionError is a TransportError."""
        error = TransportConnectionError("x", "grpc", "host", 50051)
        assert isinstance(error, TransportError)


class TestTransportConfigRepr:
    """Test TransportConfig __repr__ with password redaction."""

    def test_repr_no_password(self):
        """Test repr without password shows empty string marker."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        r = repr(config)
        assert "password=''" in r
        assert "localhost" in r

    def test_repr_with_password_redacted(self):
        """Test repr with password shows *** instead of actual password."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
            password="supersecret",
        )
        r = repr(config)
        assert "supersecret" not in r
        assert "password=***" in r

    def test_repr_contains_transport_type(self):
        """Test repr includes transport type."""
        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="10.0.0.1",
            port=50051,
        )
        r = repr(config)
        assert "GRPC" in r
        assert "10.0.0.1" in r
        assert "50051" in r


class TestDsnParsingEdgeCases:
    """Test DSN parsing edge cases and additional query params."""

    def test_insecure_tls_skip_verify_alias(self):
        """Test insecure_tls_skip_verify alias."""
        config = parse_dsn("quic://localhost:3141?insecure_tls_skip_verify=1")
        assert config.skip_verify is True

    def test_insecure_alias(self):
        """Test insecure alias for skip_verify."""
        config = parse_dsn("quic://localhost:3141?insecure=true")
        assert config.skip_verify is True

    def test_skip_verify_false_values(self):
        """Test skip_verify with false-ish values."""
        config = parse_dsn("quic://localhost:3141?skip_verify=0")
        assert config.skip_verify is False

    def test_tls_true_values(self):
        """Test various truthy TLS values."""
        for val in ("1", "true", "yes", "on"):
            config = parse_dsn(f"grpc://localhost:50051?tls={val}")
            assert config.tls_enabled is True, f"Failed for tls={val}"

    def test_tls_false_values(self):
        """Test TLS disabled with false value."""
        config = parse_dsn("grpc://localhost:50051?tls=false")
        assert config.tls_enabled is False

    def test_ca_alias(self):
        """Test ca alias for ca_cert."""
        config = parse_dsn("quic://localhost:3141?ca=/path/to/ca.pem")
        assert config.ca_cert == "/path/to/ca.pem"

    def test_cert_alias(self):
        """Test cert alias for client_cert."""
        config = parse_dsn("quic://localhost:3141?cert=/path/to/cert.pem")
        assert config.client_cert == "/path/to/cert.pem"

    def test_key_alias(self):
        """Test key alias for client_key."""
        config = parse_dsn("quic://localhost:3141?key=/path/to/key.pem")
        assert config.client_key == "/path/to/key.pem"

    def test_server_name_param(self):
        """Test server_name query parameter."""
        config = parse_dsn("quic://localhost:3141?server_name=geode.example.com")
        assert config.server_name == "geode.example.com"

    def test_hello_name_param(self):
        """Test hello_name query parameter."""
        config = parse_dsn("quic://localhost:3141?hello_name=my-client")
        assert config.hello_name == "my-client"

    def test_hello_ver_param(self):
        """Test hello_ver query parameter."""
        config = parse_dsn("quic://localhost:3141?hello_ver=2.0.0")
        assert config.hello_ver == "2.0.0"

    def test_conformance_param(self):
        """Test conformance query parameter."""
        config = parse_dsn("quic://localhost:3141?conformance=full")
        assert config.conformance == "full"

    def test_no_query_params(self):
        """Test DSN with no query parameters uses defaults."""
        config = parse_dsn("quic://10.0.0.1:3141")
        assert config.tls_enabled is True
        assert config.skip_verify is False
        assert config.username == ""
        assert config.password == ""
        assert config.page_size == 1000

    def test_no_host_defaults(self):
        """Test DSN with no host defaults to 127.0.0.1."""
        config = parse_dsn("quic://:3141")
        assert config.host == "127.0.0.1"


class TestCreateTransportEdgeCases:
    """Test create_transport edge cases."""

    def test_create_transport_invalid_type(self):
        """Test create_transport raises ValueError for unknown type."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        # Monkey-patch transport_type to something invalid
        config.transport_type = "invalid"
        with pytest.raises(ValueError, match="Unknown transport type"):
            create_transport(config)


class TestQuicTransportUnit:
    """Unit tests for QuicTransport without network."""

    def test_init(self):
        """Test QuicTransport initialization."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        assert transport.config is config
        assert transport.session_id == ""
        assert transport._connected is False
        assert transport._buffer == b""

    def test_try_read_from_buffer_empty(self):
        """Test _try_read_from_buffer with empty buffer returns None."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._buffer = bytearray()
        assert transport._try_read_from_buffer() is None

    def test_try_read_from_buffer_partial_header(self):
        """Test _try_read_from_buffer with partial length header returns None."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._buffer = bytearray(b"\x00\x00")  # Only 2 bytes, need 4
        assert transport._try_read_from_buffer() is None

    def test_try_read_from_buffer_incomplete_body(self):
        """Test _try_read_from_buffer with incomplete message body returns None."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        # Length says 100 bytes but only have header
        transport._buffer = struct.pack(">I", 100)
        assert transport._try_read_from_buffer() is None

    def test_try_read_from_buffer_oversized_message(self):
        """Test _try_read_from_buffer rejects oversized messages."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        # Create a length prefix exceeding MAX_MESSAGE_SIZE
        transport._buffer = struct.pack(">I", MAX_MESSAGE_SIZE + 1)
        with pytest.raises(TransportError, match="Message too large"):
            transport._try_read_from_buffer()

    def test_try_read_from_buffer_valid_message(self):
        """Test _try_read_from_buffer with a valid empty protobuf message."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        # Empty protobuf message (0 bytes)
        transport._buffer = bytearray(struct.pack(">I", 0))
        result = transport._try_read_from_buffer()
        assert result is not None

    @pytest.mark.asyncio
    async def test_write_message_not_connected(self):
        """Test _write_message raises when not connected."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        from geode_client.proto import QuicClientMessage

        with pytest.raises(TransportError, match="Not connected"):
            await transport._write_message(QuicClientMessage())

    @pytest.mark.asyncio
    async def test_read_message_not_connected(self):
        """Test _read_message raises when not connected."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        with pytest.raises(TransportError, match="Not connected"):
            await transport._read_message()

    @pytest.mark.asyncio
    async def test_read_message_timeout(self):
        """Test _read_message timeout raises TransportError."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._connected = True
        transport._buffer = bytearray()
        # Create a queue that never gets data
        transport._reader_queue = asyncio.Queue()
        with pytest.raises(TransportError, match="Timeout reading message"):
            await transport._read_message(read_timeout=0.01)

    @pytest.mark.asyncio
    async def test_read_message_stream_closed(self):
        """Test _read_message raises when stream sends None (closed)."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._connected = True
        transport._buffer = bytearray()
        transport._reader_queue = asyncio.Queue()
        transport._reader_queue.put_nowait(None)
        with pytest.raises(TransportError, match="Stream closed"):
            await transport._read_message()

    @pytest.mark.asyncio
    async def test_read_message_oversized(self):
        """Test _read_message rejects oversized length prefix."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._connected = True
        transport._buffer = bytearray()
        transport._reader_queue = asyncio.Queue()
        # Send a length prefix that exceeds MAX_MESSAGE_SIZE
        oversized_header = struct.pack(">I", MAX_MESSAGE_SIZE + 1)
        transport._reader_queue.put_nowait(oversized_header)
        with pytest.raises(TransportError, match="Message too large"):
            await transport._read_message()

    @pytest.mark.asyncio
    async def test_read_message_body_timeout(self):
        """Test _read_message timeout while reading body."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._connected = True
        transport._buffer = bytearray()
        transport._reader_queue = asyncio.Queue()
        # Send valid header saying 100 bytes, but no body data
        header = struct.pack(">I", 100)
        transport._reader_queue.put_nowait(header)
        with pytest.raises(TransportError, match="Timeout reading message"):
            await transport._read_message(read_timeout=0.01)

    @pytest.mark.asyncio
    async def test_read_message_body_stream_closed(self):
        """Test _read_message stream closed while reading body."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._connected = True
        transport._buffer = bytearray()
        transport._reader_queue = asyncio.Queue()
        # Send valid header then None (stream closed)
        header = struct.pack(">I", 100)
        transport._reader_queue.put_nowait(header)
        transport._reader_queue.put_nowait(None)
        with pytest.raises(TransportError, match="Stream closed"):
            await transport._read_message()

    @pytest.mark.asyncio
    async def test_read_message_valid(self):
        """Test _read_message with valid empty protobuf."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._connected = True
        transport._buffer = bytearray()
        transport._reader_queue = asyncio.Queue()
        # Empty message (0-length body)
        header = struct.pack(">I", 0)
        transport._reader_queue.put_nowait(header)
        result = await transport._read_message()
        assert result is not None

    @pytest.mark.asyncio
    async def test_close_not_connected(self):
        """Test close when not connected is no-op."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        await transport.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_connected(self):
        """Test close cleans up state."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._connected = True
        transport._protocol = MagicMock()
        transport._connection_cm = MagicMock()
        transport._connection_cm.__aexit__ = AsyncMock()
        transport._buffer = bytearray(b"some data")

        await transport.close()

        assert transport._connected is False
        assert transport._protocol is None
        assert transport._connection_cm is None
        assert transport._buffer == b""

    @pytest.mark.asyncio
    async def test_read_next_from_buffer(self):
        """Test read_next reads from buffer first."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._connected = True
        # Put a valid empty message in the buffer
        transport._buffer = bytearray(struct.pack(">I", 0))
        result = await transport.read_next()
        assert result is not None

    @pytest.mark.asyncio
    async def test_read_next_fallback_to_read_message(self):
        """Test read_next falls back to _read_message when buffer empty."""
        config = TransportConfig(
            transport_type=TransportType.QUIC,
            host="localhost",
            port=3141,
        )
        transport = QuicTransport(config)
        transport._connected = True
        transport._buffer = bytearray()
        transport._reader_queue = asyncio.Queue()
        # Put valid empty message in queue
        transport._reader_queue.put_nowait(struct.pack(">I", 0))
        result = await transport.read_next()
        assert result is not None


class TestGrpcTransportUnit:
    """Unit tests for GrpcTransport without network."""

    def test_init(self):
        """Test GrpcTransport initialization."""
        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="localhost",
            port=50051,
        )
        transport = GrpcTransport(config)
        assert transport.config is config
        assert transport.session_id == ""
        assert transport._connected is False
        assert transport._channel is None
        assert transport._stub is None

    @pytest.mark.asyncio
    async def test_close_not_connected(self):
        """Test close when not connected is no-op."""
        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="localhost",
            port=50051,
        )
        transport = GrpcTransport(config)
        await transport.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_connected(self):
        """Test close cleans up state."""
        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="localhost",
            port=50051,
        )
        transport = GrpcTransport(config)
        transport._connected = True
        transport._channel = MagicMock()
        transport._channel.close = AsyncMock()
        transport._stub = MagicMock()

        await transport.close()

        assert transport._connected is False
        assert transport._channel is None
        assert transport._stub is None

    @pytest.mark.asyncio
    async def test_ping_returns_false_on_exception(self):
        """Test ping returns False when stub raises."""
        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="localhost",
            port=50051,
        )
        transport = GrpcTransport(config)
        transport._connected = True
        transport._stub = MagicMock()
        transport._stub.Ping = AsyncMock(side_effect=Exception("network error"))
        result = await transport.ping()
        assert result is False

    @pytest.mark.asyncio
    async def test_pull_raises_not_implemented(self):
        """Test pull raises NotImplementedError for gRPC."""
        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="localhost",
            port=50051,
        )
        transport = GrpcTransport(config)
        from geode_client.proto import PullRequest

        with pytest.raises(NotImplementedError, match="Pull is not available via gRPC"):
            await transport.pull(PullRequest())

    @pytest.mark.asyncio
    async def test_read_next_no_stream(self):
        """Test read_next raises when no active stream."""
        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="localhost",
            port=50051,
        )
        transport = GrpcTransport(config)
        with pytest.raises(TransportError, match="No active Execute stream"):
            await transport.read_next()

    @pytest.mark.asyncio
    async def test_read_next_stream_ended(self):
        """Test read_next raises when stream returns None."""
        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="localhost",
            port=50051,
        )
        transport = GrpcTransport(config)
        mock_stream = MagicMock()
        mock_stream.read = AsyncMock(return_value=None)
        transport._exec_stream = mock_stream
        with pytest.raises(TransportError, match="Execute stream ended unexpectedly"):
            await transport.read_next()

    @pytest.mark.asyncio
    async def test_read_next_success(self):
        """Test read_next returns wrapped response."""
        from geode_client.proto import ExecutionResponse

        config = TransportConfig(
            transport_type=TransportType.GRPC,
            host="localhost",
            port=50051,
        )
        transport = GrpcTransport(config)
        mock_response = ExecutionResponse()
        mock_stream = MagicMock()
        mock_stream.read = AsyncMock(return_value=mock_response)
        transport._exec_stream = mock_stream
        result = await transport.read_next()
        assert result is not None
        assert result.HasField("execute")

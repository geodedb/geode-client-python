"""Unit tests for transport module - DSN parsing and transport selection."""

import warnings

import pytest

from geode_client.transport import (
    GrpcTransport,
    QuicTransport,
    TransportConfig,
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

    def test_grcp_deprecated_alias(self):
        """Test grcp:// as deprecated alias for grpc://."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = parse_dsn("grcp://localhost:50051")

            # Should emit deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "grcp://" in str(w[0].message)

            # Should parse as gRPC
            assert config.transport_type == TransportType.GRPC

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

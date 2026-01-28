"""Unit tests for Geode configuration and DSN parsing."""

from geode_client import Client
from geode_client.client import Connection, open_database


class TestClientCreation:
    """Tests for Client creation."""

    def test_default_values(self):
        """Test Client default values."""
        client = Client()
        assert client.host == "127.0.0.1"
        assert client.port == 3141

    def test_custom_host_port(self):
        """Test Client with custom host and port."""
        client = Client(host="geode.example.com", port=9999)
        assert client.host == "geode.example.com"
        assert client.port == 9999

    def test_config_dict(self):
        """Test Client stores config dict."""
        client = Client(host="test", port=1234, skip_verify=True)
        assert client.config["host"] == "test"
        assert client.config["port"] == 1234
        assert client.config["skip_verify"] is True


class TestClientFromUrl:
    """Tests for Client.from_url DSN parsing."""

    def test_simple_url(self):
        """Test simple URL parsing."""
        client = Client.from_url("quic://localhost:3141")
        assert client.host == "localhost"
        assert client.port == 3141

    def test_geode_scheme(self):
        """Test geode:// scheme."""
        client = Client.from_url("geode://localhost:3141")
        assert client.host == "localhost"
        assert client.port == 3141

    def test_host_only(self):
        """Test URL with host only (default port)."""
        client = Client.from_url("quic://geode.example.com")
        assert client.host == "geode.example.com"
        assert client.port == 3141  # Default

    def test_ipv4_address(self):
        """Test IPv4 address."""
        client = Client.from_url("quic://192.168.1.100:8443")
        assert client.host == "192.168.1.100"
        assert client.port == 8443

    def test_ipv6_address(self):
        """Test IPv6 address."""
        client = Client.from_url("quic://[::1]:3141")
        assert client.host == "::1"
        assert client.port == 3141

    def test_ipv6_address_no_port(self):
        """Test IPv6 address without port."""
        client = Client.from_url("quic://[::1]")
        assert client.host == "::1"
        assert client.port == 3141

    def test_ipv6_full_address(self):
        """Test full IPv6 address."""
        client = Client.from_url("quic://[2001:db8::1]:8443")
        assert client.host == "2001:db8::1"
        assert client.port == 8443


class TestUrlQueryParameters:
    """Tests for URL query parameter parsing."""

    def test_page_size(self):
        """Test page_size parameter."""
        client = Client.from_url("quic://localhost:3141?page_size=500")
        assert client.config["page_size"] == 500

    def test_hello_name(self):
        """Test hello_name parameter."""
        client = Client.from_url("quic://localhost?hello_name=my-app")
        assert client.config["hello_name"] == "my-app"

    def test_hello_ver(self):
        """Test hello_ver parameter."""
        client = Client.from_url("quic://localhost?hello_ver=2.0.0")
        assert client.config["hello_ver"] == "2.0.0"

    def test_conformance(self):
        """Test conformance parameter."""
        client = Client.from_url("quic://localhost?conformance=full")
        assert client.config["conformance"] == "full"

    def test_skip_verify_true(self):
        """Test skip_verify=true."""
        client = Client.from_url("quic://localhost?skip_verify=true")
        assert client.config["skip_verify"] is True

    def test_skip_verify_1(self):
        """Test skip_verify=1."""
        client = Client.from_url("quic://localhost?skip_verify=1")
        assert client.config["skip_verify"] is True

    def test_skip_verify_false(self):
        """Test skip_verify=false."""
        client = Client.from_url("quic://localhost?skip_verify=false")
        assert client.config["skip_verify"] is False

    def test_skip_verify_0(self):
        """Test skip_verify=0."""
        client = Client.from_url("quic://localhost?skip_verify=0")
        assert client.config["skip_verify"] is False

    def test_ca_cert(self):
        """Test ca_cert parameter."""
        client = Client.from_url("quic://localhost?ca_cert=/path/to/ca.crt")
        assert client.config["ca_cert"] == "/path/to/ca.crt"

    def test_client_cert(self):
        """Test client_cert parameter."""
        client = Client.from_url("quic://localhost?client_cert=/path/to/client.crt")
        assert client.config["client_cert"] == "/path/to/client.crt"

    def test_client_key(self):
        """Test client_key parameter."""
        client = Client.from_url("quic://localhost?client_key=/path/to/client.key")
        assert client.config["client_key"] == "/path/to/client.key"

    def test_server_name(self):
        """Test server_name parameter."""
        client = Client.from_url("quic://localhost?server_name=custom.example.com")
        assert client.config["server_name"] == "custom.example.com"

    def test_multiple_parameters(self):
        """Test multiple query parameters."""
        url = "quic://localhost:8443?page_size=1000&skip_verify=true&conformance=full"
        client = Client.from_url(url)
        assert client.config["page_size"] == 1000
        assert client.config["skip_verify"] is True
        assert client.config["conformance"] == "full"


class TestUrlDefaultValues:
    """Tests for URL parsing default values."""

    def test_default_host(self):
        """Test default host when not specified."""
        client = Client.from_url("quic://")
        assert client.host == "127.0.0.1"

    def test_default_port(self):
        """Test default port when not specified."""
        client = Client.from_url("quic://example.com")
        assert client.port == 3141

    def test_empty_query_string(self):
        """Test URL with empty query string."""
        client = Client.from_url("quic://localhost:3141?")
        assert client.host == "localhost"
        assert client.port == 3141


class TestOpenDatabase:
    """Tests for open_database function."""

    def test_returns_client(self):
        """Test open_database returns Client."""
        client = open_database("quic://localhost:3141")
        assert isinstance(client, Client)

    def test_parses_url(self):
        """Test open_database parses URL correctly."""
        client = open_database("quic://test.local:9999?skip_verify=true")
        assert client.host == "test.local"
        assert client.port == 9999
        assert client.config["skip_verify"] is True


class TestConnectionCreation:
    """Tests for Connection creation."""

    def test_default_values(self):
        """Test Connection default values."""
        conn = Connection()
        assert conn.host == "127.0.0.1"
        assert conn.port == 3141
        assert conn.page_size == 1000
        assert conn.hello_name == "geode-python"
        assert conn.hello_ver == "0.1.0"
        assert conn.conformance == "min"
        assert conn.skip_verify is False

    def test_localhost_normalized(self):
        """Test localhost is normalized to 127.0.0.1."""
        conn = Connection(host="localhost")
        assert conn.host == "127.0.0.1"

    def test_custom_host_preserved(self):
        """Test custom host is preserved."""
        conn = Connection(host="geode.example.com")
        assert conn.host == "geode.example.com"

    def test_custom_port(self):
        """Test custom port."""
        conn = Connection(port=9999)
        assert conn.port == 9999

    def test_custom_page_size(self):
        """Test custom page_size."""
        conn = Connection(page_size=500)
        assert conn.page_size == 500

    def test_custom_hello_name(self):
        """Test custom hello_name."""
        conn = Connection(hello_name="my-app")
        assert conn.hello_name == "my-app"

    def test_custom_hello_ver(self):
        """Test custom hello_ver."""
        conn = Connection(hello_ver="2.0.0")
        assert conn.hello_ver == "2.0.0"

    def test_custom_conformance(self):
        """Test custom conformance."""
        conn = Connection(conformance="full")
        assert conn.conformance == "full"

    def test_tls_options(self):
        """Test TLS options."""
        conn = Connection(
            ca_cert="/path/to/ca.crt",
            client_cert="/path/to/client.crt",
            client_key="/path/to/client.key",
            skip_verify=True,
            server_name="custom.example.com",
        )
        assert conn.ca_cert == "/path/to/ca.crt"
        assert conn.client_cert == "/path/to/client.crt"
        assert conn.client_key == "/path/to/client.key"
        assert conn.skip_verify is True
        assert conn.server_name == "custom.example.com"

    def test_server_name_defaults_to_host(self):
        """Test server_name defaults to host."""
        conn = Connection(host="geode.example.com")
        assert conn.server_name == "geode.example.com"

    def test_server_name_defaults_to_normalized_host(self):
        """Test server_name uses normalized host."""
        conn = Connection(host="localhost")
        assert conn.server_name == "127.0.0.1"


class TestClientConnection:
    """Tests for Client.connection method."""

    def test_returns_connection(self):
        """Test connection() returns Connection."""
        client = Client(host="test.local", port=9999)
        conn = client.connection()
        assert isinstance(conn, Connection)

    def test_passes_config(self):
        """Test connection() passes config to Connection."""
        client = Client(host="test.local", port=9999, skip_verify=True, page_size=500)
        conn = client.connection()
        assert conn.host == "test.local"
        assert conn.port == 9999
        assert conn.skip_verify is True
        assert conn.page_size == 500


class TestUrlEdgeCases:
    """Tests for URL parsing edge cases."""

    def test_url_with_trailing_slash(self):
        """Test URL with trailing slash."""
        client = Client.from_url("quic://localhost:3141/")
        assert client.host == "localhost"
        assert client.port == 3141

    def test_url_with_path(self):
        """Test URL with path (path is ignored)."""
        client = Client.from_url("quic://localhost:3141/database")
        assert client.host == "localhost"
        assert client.port == 3141

    def test_url_case_insensitive_scheme(self):
        """Test URL scheme is case insensitive."""
        client = Client.from_url("QUIC://localhost:3141")
        assert client.host == "localhost"

    def test_port_as_string_in_query(self):
        """Test page_size as string is converted to int."""
        client = Client.from_url("quic://localhost?page_size=500")
        assert client.config["page_size"] == 500
        assert isinstance(client.config["page_size"], int)


class TestDataclasses:
    """Tests for dataclass definitions."""

    def test_column_dataclass(self):
        """Test Column dataclass."""
        from geode_client.client import Column

        col = Column(name="id", type="INT")
        assert col.name == "id"
        assert col.type == "INT"

    def test_page_dataclass(self):
        """Test Page dataclass."""
        from geode_client.client import Column, Page

        page = Page(
            columns=[Column(name="x", type="INT")],
            rows=[],
            ordered=True,
            order_keys=["x"],
            final=True,
        )
        assert len(page.columns) == 1
        assert page.ordered is True
        assert page.order_keys == ["x"]
        assert page.final is True

    def test_page_default_order_keys(self):
        """Test Page default order_keys."""
        from geode_client.client import Page

        page = Page(columns=[], rows=[])
        assert page.order_keys == []

    def test_savepoint_dataclass(self):
        """Test Savepoint dataclass."""
        from geode_client.client import Savepoint

        sp = Savepoint(name="sp1")
        assert sp.name == "sp1"
        assert sp.connection is None


class TestConnectionState:
    """Tests for Connection initial state."""

    def test_initial_not_connected(self):
        """Test connection is initially not connected."""
        conn = Connection()
        assert conn._connected is False
        assert conn._protocol is None
        assert conn._reader is None
        assert conn._writer is None

    def test_initial_buffer_empty(self):
        """Test initial buffer is empty."""
        conn = Connection()
        assert conn._buffer == b""

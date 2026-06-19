"""Unit tests for format_dsn (inverse of parse_dsn)."""

from geode_client import format_dsn, parse_dsn
from geode_client.transport import TransportConfig, TransportType


class TestFormatDSN:
    def test_minimal(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC, host="127.0.0.1", port=3141
        )
        assert format_dsn(cfg) == "quic://127.0.0.1:3141"

    def test_grpc_scheme(self):
        cfg = TransportConfig(transport_type=TransportType.GRPC, host="h", port=50051)
        assert format_dsn(cfg).startswith("grpc://h:50051")

    def test_emits_non_default_params(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC,
            host="h",
            port=3141,
            graph="mydb",
            tenant="acme",
            role="analyst",
        )
        out = format_dsn(cfg)
        assert "graph=mydb" in out
        assert "tenant=acme" in out
        assert "role=analyst" in out

    def test_omits_default_params(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC,
            host="h",
            port=3141,
            page_size=1000,  # default
            conformance="min",  # default
        )
        out = format_dsn(cfg)
        assert "page_size" not in out
        assert "conformance" not in out

    def test_credentials_userinfo(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC,
            host="h",
            port=3141,
            username="alice",
            password="s3cr3t",
        )
        out = format_dsn(cfg)
        assert out.startswith("quic://alice:s3cr3t@h:3141")

    def test_password_only_query_param(self):
        cfg = TransportConfig(
            transport_type=TransportType.QUIC,
            host="h",
            port=3141,
            password="s3cr3t",
        )
        out = format_dsn(cfg)
        assert "@" not in out
        assert "pass=s3cr3t" in out

    def test_skip_verify_and_tls_disabled(self):
        cfg = TransportConfig(
            transport_type=TransportType.GRPC,
            host="h",
            port=50051,
            skip_verify=True,
            tls_enabled=False,
        )
        out = format_dsn(cfg)
        assert "insecure_tls_skip_verify=true" in out
        assert "tls=0" in out

    def test_ipv6_bracketed(self):
        cfg = TransportConfig(transport_type=TransportType.QUIC, host="::1", port=3141)
        out = format_dsn(cfg)
        assert "[::1]:3141" in out


class TestRoundTrip:
    def test_parse_format_parse(self):
        original = (
            "quic://alice:s3cr3t@127.0.0.1:3141?graph=mydb&tenant=acme&role=analyst"
        )
        cfg = parse_dsn(original)
        formatted = format_dsn(cfg)
        cfg2 = parse_dsn(formatted)
        assert cfg2.host == cfg.host
        assert cfg2.port == cfg.port
        assert cfg2.transport_type == cfg.transport_type
        assert cfg2.username == cfg.username
        assert cfg2.password == cfg.password
        assert cfg2.graph == cfg.graph
        assert cfg2.tenant == cfg.tenant
        assert cfg2.role == cfg.role

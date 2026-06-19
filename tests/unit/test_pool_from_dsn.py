"""Unit tests for create_pool_from_dsn factory."""

from geode_client import ConnectionPool, create_pool_from_dsn
from geode_client.transport import TransportType


class TestCreatePoolFromDSN:
    def test_builds_pool_from_dsn(self):
        pool = create_pool_from_dsn("quic://localhost:3141?graph=mydb")
        assert isinstance(pool, ConnectionPool)
        # localhost normalized to 127.0.0.1 by parse_dsn
        assert pool.client.host == "127.0.0.1"
        assert pool.client.port == 3141

    def test_carries_transport_type(self):
        pool = create_pool_from_dsn("grpc://localhost:50051")
        assert pool.client.config["transport_type"] == TransportType.GRPC
        assert pool.client.port == 50051

    def test_carries_tenant_role_graph(self):
        pool = create_pool_from_dsn(
            "quic://localhost:3141?tenant_id=acme&role=analyst&graph=g"
        )
        cfg = pool.client.config
        assert cfg["tenant"] == "acme"
        assert cfg["role"] == "analyst"
        assert cfg["graph"] == "g"

    def test_pool_sizing_kwargs(self):
        pool = create_pool_from_dsn("quic://localhost:3141", min_size=2, max_size=7)
        assert pool.min_size == 2
        assert pool.max_size == 7

    def test_not_initialized(self):
        pool = create_pool_from_dsn("quic://localhost:3141")
        assert pool._initialized is False

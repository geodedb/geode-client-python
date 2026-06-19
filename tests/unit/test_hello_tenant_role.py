"""Unit tests for HELLO tenant_id and role config + DSN parsing."""

from unittest.mock import MagicMock

import pytest

from geode_client.client import Connection
from geode_client.transport import TransportConfig, TransportType, parse_dsn


class TestDSNTenantRole:
    def test_tenant_id_param(self):
        cfg = parse_dsn("quic://localhost:3141?tenant_id=acme")
        assert cfg.tenant == "acme"

    def test_tenant_alias(self):
        cfg = parse_dsn("quic://localhost:3141?tenant=acme")
        assert cfg.tenant == "acme"

    def test_role_param(self):
        cfg = parse_dsn("quic://localhost:3141?role=analyst")
        assert cfg.role == "analyst"

    def test_defaults_empty(self):
        cfg = parse_dsn("quic://localhost:3141")
        assert cfg.tenant == ""
        assert cfg.role == ""

    def test_config_defaults(self):
        cfg = TransportConfig(transport_type=TransportType.QUIC, host="h", port=1)
        assert cfg.tenant == ""
        assert cfg.role == ""


class TestConnectionHello:
    def test_connection_accepts_tenant_role(self):
        conn = Connection(host="h", port=1, tenant="acme", role="analyst")
        assert conn.tenant == "acme"
        assert conn.role == "analyst"

    @pytest.mark.asyncio
    async def test_hello_request_includes_tenant_and_role(self, monkeypatch):
        conn = Connection(host="h", port=1, tenant="acme", role="analyst")

        captured = {}

        class FakeTransport:
            session_id = "s1"

            async def connect(self):
                return None

            async def hello(self, req):
                captured["req"] = req
                resp = MagicMock()
                resp.success = True
                resp.error_message = ""
                return resp

            async def close(self):
                return None

        monkeypatch.setattr(
            "geode_client.client.create_transport",
            lambda config: FakeTransport(),
        )
        await conn.connect()
        req = captured["req"]
        assert req.tenant_id == "acme"
        assert req.role == "analyst"

    @pytest.mark.asyncio
    async def test_hello_request_omits_empty_tenant_role(self, monkeypatch):
        conn = Connection(host="h", port=1)
        captured = {}

        class FakeTransport:
            session_id = "s1"

            async def connect(self):
                return None

            async def hello(self, req):
                captured["req"] = req
                resp = MagicMock()
                resp.success = True
                resp.error_message = ""
                return resp

            async def close(self):
                return None

        monkeypatch.setattr(
            "geode_client.client.create_transport",
            lambda config: FakeTransport(),
        )
        await conn.connect()
        req = captured["req"]
        assert req.HasField("tenant_id") is False
        assert req.HasField("role") is False

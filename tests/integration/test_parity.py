"""Integration tests for driver-parity features.

These require a running Geode server (or Docker). They are marked
`integration` (auto-applied by conftest) and skipped without a server, but
must import and collect cleanly under pytest.
"""

import pytest

from geode_client import (
    Cipher,
    NoRowsError,
    Statement,
    as_node,
    create_pool_from_dsn,
    parse_schema_fs,
)
from geode_client.types import ValueKind


@pytest.mark.asyncio
class TestParityIntegration:
    async def test_query_row_returns_row(self, connection):
        row = await connection.query_row("RETURN 1 AS x")
        assert row["x"].as_int == 1

    async def test_query_row_no_rows_raises(self, connection):
        with pytest.raises(NoRowsError):
            await connection.query_row("MATCH (n:DoesNotExist12345) RETURN n LIMIT 1")

    async def test_batch_exec_single_transaction(self, connection):
        await connection.batch_exec(
            [
                Statement("CREATE (:ParityTest {n: 1})"),
                Statement("CREATE (:ParityTest {n: 2})"),
            ]
        )
        page, _ = await connection.query("MATCH (p:ParityTest) RETURN count(p) AS c")
        assert page.rows[0]["c"].as_int >= 2

    async def test_pipeline_exec(self, connection):
        stmts = [Statement(f"CREATE (:PipeTest {{i: {i}}})") for i in range(50)]
        await connection.pipeline_exec(stmts, chunk_size=10, max_workers=4)

    async def test_as_node_conversion(self, connection):
        await connection.execute("CREATE (:NodeConv {name: 'Alice'})")
        page, _ = await connection.query("MATCH (n:NodeConv) RETURN n LIMIT 1")
        value = page.rows[0]["n"]
        if value.kind == ValueKind.NODE:
            node = as_node(value)
            assert "NodeConv" in node.labels


def test_parse_schema_fs_with_tmp(tmp_path):
    """parse_schema_fs is server-independent; exercise it during collection."""
    (tmp_path / "schema.gql").write_text("CREATE (:Seed {ok: true});")
    stmts = parse_schema_fs(tmp_path)
    assert stmts and stmts[0].query.startswith("CREATE")


def test_cipher_round_trip_no_server():
    """Crypto is server-independent."""
    cipher = Cipher(b"0123456789abcdef0123456789abcdef")
    assert cipher.decrypt_string(cipher.encrypt_string("hello")) == "hello"


def test_create_pool_from_dsn_builds_without_connecting():
    """Factory builds an uninitialized pool without contacting a server."""
    pool = create_pool_from_dsn("quic://localhost:3141?graph=g")
    assert pool.client.port == 3141

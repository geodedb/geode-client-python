"""Unit tests for Connection.query_row / fetch_one."""

import pytest

from geode_client import NoRowsError, Value, ValueKind
from geode_client.client import Column, Connection, Page


def _conn_with_page(page):
    conn = Connection(host="h", port=1)
    conn._connected = True

    async def fake_query(text, params=None, page_size=None):
        async def empty_pager():
            return
            yield  # pragma: no cover

        return page, empty_pager

    conn.query = fake_query  # type: ignore[method-assign]
    return conn


class TestQueryRow:
    @pytest.mark.asyncio
    async def test_returns_first_row(self):
        row = {"x": Value(kind=ValueKind.INT, int_value=42)}
        page = Page(columns=[Column(name="x", type="INT")], rows=[row], final=True)
        conn = _conn_with_page(page)
        result = await conn.query_row("RETURN 1 AS x")
        assert result["x"].as_int == 42

    @pytest.mark.asyncio
    async def test_raises_no_rows_when_empty(self):
        page = Page(columns=[Column(name="x", type="INT")], rows=[], final=True)
        conn = _conn_with_page(page)
        with pytest.raises(NoRowsError):
            await conn.query_row("MATCH (n) RETURN n")

    @pytest.mark.asyncio
    async def test_fetch_one_alias(self):
        row = {"x": Value(kind=ValueKind.INT, int_value=7)}
        page = Page(columns=[Column(name="x", type="INT")], rows=[row], final=True)
        conn = _conn_with_page(page)
        result = await conn.fetch_one("RETURN 7 AS x")
        assert result["x"].as_int == 7

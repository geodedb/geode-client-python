"""Unit tests for parse_schema_fs."""

import pytest

from geode_client import Statement, parse_schema_fs


@pytest.fixture
def schema_dir(tmp_path):
    (tmp_path / "01_nodes.gql").write_text(
        "// comment line\n"
        "-- sql style comment\n"
        "\n"
        "CREATE (n:Person {name: 'Alice'});\n"
        "MERGE (m:Company {name: 'Acme'});\n"
        "SELECT 1;\n"  # non-GQL keyword, dropped
    )
    (tmp_path / "02_edges.gql").write_text(
        "MATCH (a), (b) CREATE (a)-[:KNOWS]->(b);\n" "DELETE (x);\n"
    )
    (tmp_path / "notes.txt").write_text("CREATE (ignored);")  # non-.gql
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "03_more.gql").write_text("CREATE (ignored);")  # subdir not traversed
    return tmp_path


class TestParseSchemaFS:
    def test_returns_statements(self, schema_dir):
        stmts = parse_schema_fs(schema_dir)
        queries = [s.query for s in stmts]
        assert "CREATE (n:Person {name: 'Alice'})" in queries
        assert "MERGE (m:Company {name: 'Acme'})" in queries
        assert "MATCH (a), (b) CREATE (a)-[:KNOWS]->(b)" in queries
        assert "DELETE (x)" in queries

    def test_filters_comments_and_blanks(self, schema_dir):
        stmts = parse_schema_fs(schema_dir)
        for s in stmts:
            assert s.query.strip() != ""
            assert not s.query.startswith("//")
            assert not s.query.startswith("--")

    def test_drops_non_gql_keywords(self, schema_dir):
        stmts = parse_schema_fs(schema_dir)
        assert all(not s.query.upper().startswith("SELECT") for s in stmts)

    def test_ignores_non_gql_files(self, schema_dir):
        stmts = parse_schema_fs(schema_dir)
        assert all("ignored" not in s.query for s in stmts)

    def test_does_not_traverse_subdirs(self, schema_dir):
        stmts = parse_schema_fs(schema_dir)
        assert all("ignored" not in s.query for s in stmts)

    def test_semicolon_split_multiple_per_line(self, tmp_path):
        (tmp_path / "x.gql").write_text("CREATE (a); CREATE (b);")
        stmts = parse_schema_fs(tmp_path)
        assert [s.query for s in stmts] == ["CREATE (a)", "CREATE (b)"]

    def test_missing_dir_raises(self, tmp_path):
        with pytest.raises(OSError):
            parse_schema_fs(tmp_path / "nope")

    def test_statement_no_params_default(self):
        s = Statement(query="MATCH (n) RETURN n")
        assert s.query == "MATCH (n) RETURN n"
        assert s.params is None

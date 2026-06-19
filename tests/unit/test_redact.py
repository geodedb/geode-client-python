"""Unit tests for redact_dsn."""

from geode_client import redact_dsn


class TestRedactDSN:
    def test_empty(self):
        assert redact_dsn("") == ""

    def test_userinfo_user_pass(self):
        out = redact_dsn("quic://alice:s3cr3t@localhost:3141")
        assert "alice" not in out
        assert "s3cr3t" not in out
        assert "***:***@localhost:3141" in out

    def test_userinfo_user_only(self):
        out = redact_dsn("quic://alice@localhost:3141")
        assert "alice" not in out
        assert "***@localhost:3141" in out

    def test_query_params(self):
        out = redact_dsn("quic://localhost:3141?user=alice&pass=s3cr3t&graph=mydb")
        assert "alice" not in out
        assert "s3cr3t" not in out
        assert "graph=mydb" in out
        assert "user=***" in out
        assert "pass=***" in out

    def test_password_param_variants(self):
        out = redact_dsn("quic://localhost:3141?username=bob&password=hunter2")
        assert "bob" not in out
        assert "hunter2" not in out

    def test_no_creds_unchanged(self):
        dsn = "quic://localhost:3141?graph=mydb"
        assert redact_dsn(dsn) == dsn

    def test_no_scheme_bare_userinfo(self):
        out = redact_dsn("alice:s3cr3t@localhost:3141")
        assert "alice" not in out
        assert "s3cr3t" not in out

    def test_param_without_value_preserved(self):
        out = redact_dsn("quic://localhost:3141?flag&pass=x")
        assert "flag" in out
        assert "pass=***" in out

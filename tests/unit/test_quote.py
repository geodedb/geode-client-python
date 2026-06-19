"""Unit tests for quoting helpers (quote.py)."""

import pytest

from geode_client import (
    InvalidIdentifierError,
    InvalidStringError,
    quote_ident,
    quote_string,
    sanitize_graph_name,
)


class TestQuoteIdent:
    @pytest.mark.parametrize(
        "name",
        ["abc", "_abc", "Abc123", "005_add_index", "a-b-c", "X1", "snake_case"],
    )
    def test_valid_returns_name(self, name):
        assert quote_ident(name) == name

    def test_empty_raises(self):
        with pytest.raises(InvalidIdentifierError):
            quote_ident("")

    def test_leading_hyphen_raises(self):
        with pytest.raises(InvalidIdentifierError):
            quote_ident("-bad")

    @pytest.mark.parametrize("name", ["bad name", "a.b", "a'b", "a;b", "a)b", "a\\b"])
    def test_forbidden_chars_raise(self, name):
        with pytest.raises(InvalidIdentifierError):
            quote_ident(name)

    def test_digit_first_allowed(self):
        assert quote_ident("9lives") == "9lives"


class TestQuoteString:
    def test_simple(self):
        assert quote_string("hello") == "'hello'"

    def test_single_quote_doubled(self):
        assert quote_string("O'Brien") == "'O''Brien'"

    def test_backslash_escaped_first(self):
        # Backslash doubled, then quotes doubled.
        assert quote_string("a\\b") == "'a\\\\b'"

    def test_backslash_then_quote(self):
        assert quote_string("a\\'b") == "'a\\\\''b'"

    def test_empty(self):
        assert quote_string("") == "''"

    @pytest.mark.parametrize("ch", ["\x00", "\x1f", "\x7f", "\n", "\t", "\r"])
    def test_control_chars_rejected(self, ch):
        with pytest.raises(InvalidStringError):
            quote_string(f"a{ch}b")

    def test_space_allowed(self):
        assert quote_string("hello world") == "'hello world'"


class TestSanitizeGraphName:
    def test_strips_forbidden(self):
        assert sanitize_graph_name("my graph!@#") == "mygraph"

    def test_keeps_allowed(self):
        assert sanitize_graph_name("My_Graph-01") == "My_Graph-01"

    def test_empty(self):
        assert sanitize_graph_name("") == ""

    def test_all_stripped(self):
        assert sanitize_graph_name("!@#$%^&*()") == ""

    def test_no_error_on_injection(self):
        # Sanitize never raises; it strips.
        assert sanitize_graph_name("g'; DROP") == "gDROP"

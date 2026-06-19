"""
Property-based tests for geode_client using Hypothesis.

Tests the robustness of:
- DSN/URL parsing
- Value type conversions
- JSON frame parsing
- Query builder with arbitrary strings
- Pattern builder with arbitrary patterns
"""

import json
from decimal import Decimal

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from geode_client import (
    Client,
    Connection,
    ConnectionPool,
    EdgeDirection,
    PatternBuilder,
    PredicateBuilder,
    QueryBuilder,
    Value,
    ValueKind,
)
from geode_client.types import decode_value

# ============================================================================
# Custom strategies
# ============================================================================

# Valid hostname characters
hostname_chars = st.sampled_from(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-."
)

# Valid hostnames (simplified)
hostnames = st.from_regex(r"[a-zA-Z][a-zA-Z0-9\-\.]{0,62}", fullmatch=True)

# Valid ports
ports = st.integers(min_value=1, max_value=65535)

# Valid page sizes
page_sizes = st.integers(min_value=1, max_value=100000)

# Boolean-like strings
bool_strings = st.sampled_from(
    ["true", "false", "1", "0", "True", "False", "TRUE", "FALSE"]
)

# Valid parameter names (alphanumeric with underscores)
param_names = st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]{0,63}", fullmatch=True)

# Valid GQL identifiers
identifiers = st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]{0,30}", fullmatch=True)

# Node labels
labels = st.from_regex(r"[A-Z][a-zA-Z0-9_]{0,20}", fullmatch=True)

# Decimal strings
decimal_strings = st.from_regex(r"-?[0-9]+(\.[0-9]+)?", fullmatch=True)

# Date strings (YYYY-MM-DD format)
date_strings = st.builds(
    lambda y, m, d: f"{y:04d}-{m:02d}-{d:02d}",
    y=st.integers(min_value=1900, max_value=2100),
    m=st.integers(min_value=1, max_value=12),
    d=st.integers(min_value=1, max_value=28),  # Safe for all months
)

# Timestamp strings (ISO format)
timestamp_strings = st.builds(
    lambda y, m, d, h, mi, s: f"{y:04d}-{m:02d}-{d:02d}T{h:02d}:{mi:02d}:{s:02d}",
    y=st.integers(min_value=1900, max_value=2100),
    m=st.integers(min_value=1, max_value=12),
    d=st.integers(min_value=1, max_value=28),
    h=st.integers(min_value=0, max_value=23),
    mi=st.integers(min_value=0, max_value=59),
    s=st.integers(min_value=0, max_value=59),
)

# JSON-like values for decode_value testing
json_primitives = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**31), max_value=2**31 - 1),
    st.text(max_size=100),
)


# ============================================================================
# URL/DSN parsing property tests
# ============================================================================


class TestURLParsingProperties:
    """Property tests for URL/DSN parsing."""

    @given(host=hostnames, port=ports)
    @settings(max_examples=100)
    def test_simple_url_roundtrip(self, host, port):
        """Client.from_url should handle valid host:port URLs."""
        url = f"quic://{host}:{port}"
        client = Client.from_url(url)
        # Note: urlparse normalizes hostnames to lowercase (per RFC 3986)
        assert client.config["host"] == host.lower()
        assert client.config["port"] == port

    @given(host=hostnames, port=ports, page_size=page_sizes)
    @settings(max_examples=100)
    def test_url_with_page_size(self, host, port, page_size):
        """URLs with page_size parameter should parse correctly."""
        url = f"quic://{host}:{port}?page_size={page_size}"
        client = Client.from_url(url)
        assert client.config["page_size"] == page_size

    @given(host=hostnames, port=ports, skip_verify=bool_strings)
    @settings(max_examples=100)
    def test_url_with_skip_verify(self, host, port, skip_verify):
        """URLs with skip_verify parameter should parse correctly."""
        url = f"quic://{host}:{port}?skip_verify={skip_verify}"
        client = Client.from_url(url)
        expected = skip_verify.lower() in ("1", "true")
        assert client.config.get("skip_verify", False) == expected

    @given(
        host=hostnames,
        port=ports,
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.isalnum()),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
    def test_url_with_hello_name(self, host, port, name):
        """URLs with hello_name parameter should parse correctly."""
        url = f"quic://{host}:{port}?hello_name={name}"
        client = Client.from_url(url)
        assert client.config.get("hello_name") == name

    @given(arbitrary_string=st.text(max_size=200))
    @settings(max_examples=100)
    def test_arbitrary_url_doesnt_crash(self, arbitrary_string):
        """Arbitrary strings should not crash the URL parser."""
        try:
            client = Client.from_url(arbitrary_string)
            # If it succeeds, config should be a dict
            assert isinstance(client.config, dict)
        except (ValueError, TypeError, KeyError):
            # These are acceptable failures for malformed URLs
            pass


class TestConnectionConfigProperties:
    """Property tests for Connection configuration."""

    @given(host=hostnames, port=ports)
    @settings(max_examples=100)
    def test_connection_config(self, host, port):
        """Connection should accept valid host/port."""
        conn = Connection(host=host, port=port)
        assert conn.host == host
        assert conn.port == port

    @given(page_size=page_sizes)
    @settings(max_examples=100)
    def test_connection_page_size(self, page_size):
        """Connection should accept valid page sizes."""
        conn = Connection(page_size=page_size)
        assert conn.page_size == page_size

    @given(host=hostnames, port=ports, page_size=page_sizes, skip_verify=st.booleans())
    @settings(max_examples=100)
    def test_connection_all_params(self, host, port, page_size, skip_verify):
        """Connection should accept all valid parameters."""
        conn = Connection(
            host=host, port=port, page_size=page_size, skip_verify=skip_verify
        )
        assert conn.host == host
        assert conn.port == port
        assert conn.page_size == page_size
        assert conn.skip_verify == skip_verify


# ============================================================================
# Value type conversion property tests
# ============================================================================


class TestValueConversionProperties:
    """Property tests for Value type conversions."""

    @given(value=st.integers(min_value=-(2**63), max_value=2**63 - 1))
    @settings(max_examples=200)
    def test_decode_int_roundtrip(self, value):
        """Integers should decode correctly."""
        result = decode_value(value, "INT")
        assert result.kind == ValueKind.INT
        assert result.as_int == value

    @given(value=st.booleans())
    @settings(max_examples=50)
    def test_decode_bool_roundtrip(self, value):
        """Booleans should decode correctly."""
        result = decode_value(value, "BOOL")
        assert result.kind == ValueKind.BOOL
        assert result.as_bool == value

    @given(value=st.text(max_size=1000))
    @settings(max_examples=200)
    def test_decode_string_roundtrip(self, value):
        """Strings should decode correctly."""
        result = decode_value(value, "STRING")
        assert result.kind == ValueKind.STRING
        assert result.as_string == value

    @given(value=decimal_strings)
    @settings(max_examples=200)
    def test_decode_decimal_roundtrip(self, value):
        """Decimal strings should decode correctly."""
        result = decode_value(value, "DECIMAL")
        assert result.kind == ValueKind.DECIMAL
        expected = Decimal(value)
        assert result.as_decimal == expected

    @given(value=date_strings)
    @settings(max_examples=100)
    def test_decode_date_roundtrip(self, value):
        """Date strings should decode correctly."""
        result = decode_value(value, "DATE")
        assert result.kind == ValueKind.DATE
        assert result.str_value == value

    @given(value=timestamp_strings)
    @settings(max_examples=100)
    def test_decode_timestamp_roundtrip(self, value):
        """Timestamp strings should decode correctly."""
        result = decode_value(value, "TIMESTAMP")
        assert result.kind == ValueKind.TIMESTAMP
        assert result.str_value == value

    @given(value=st.none())
    def test_decode_null(self, value):
        """None should decode to NULL."""
        result = decode_value(value, "")
        assert result.kind == ValueKind.NULL
        assert result.is_null

    @given(elements=st.lists(st.integers(min_value=-1000, max_value=1000), max_size=50))
    @settings(max_examples=100)
    def test_decode_array_of_ints(self, elements):
        """Integer arrays should decode correctly."""
        result = decode_value(elements, "")
        assert result.kind == ValueKind.ARRAY
        assert len(result.as_array) == len(elements)

    @given(
        d=st.dictionaries(
            keys=st.text(min_size=1, max_size=20).filter(str.isidentifier),
            values=st.integers(min_value=-1000, max_value=1000),
            max_size=20,
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
    def test_decode_object(self, d):
        """Objects should decode correctly."""
        result = decode_value(d, "")
        assert result.kind == ValueKind.OBJECT
        assert len(result.as_object) == len(d)

    @given(value=st.binary(max_size=100))
    @settings(max_examples=100)
    def test_decode_bytea_hex(self, value):
        """Bytea hex strings should decode correctly."""
        hex_str = "\\x" + value.hex()
        result = decode_value(hex_str, "BYTEA")
        assert result.kind == ValueKind.BYTEA
        assert result.bytes_value == value


class TestValueConstructionProperties:
    """Property tests for Value construction."""

    @given(value=st.integers(min_value=-(2**63), max_value=2**63 - 1))
    @settings(max_examples=100)
    def test_construct_int(self, value):
        """INT values should construct correctly."""
        v = Value(kind=ValueKind.INT, int_value=value)
        assert v.as_int == value
        assert v.raw_value == value

    @given(value=st.booleans())
    @settings(max_examples=50)
    def test_construct_bool(self, value):
        """BOOL values should construct correctly."""
        v = Value(kind=ValueKind.BOOL, bool_value=value)
        assert v.as_bool == value
        assert v.raw_value == value

    @given(value=st.text(max_size=500))
    @settings(max_examples=100)
    def test_construct_string(self, value):
        """STRING values should construct correctly."""
        v = Value(kind=ValueKind.STRING, str_value=value)
        assert v.as_string == value
        assert v.raw_value == value

    @given(value=st.decimals(allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_construct_decimal(self, value):
        """DECIMAL values should construct correctly."""
        v = Value(kind=ValueKind.DECIMAL, decimal_value=value)
        assert v.as_decimal == value


# ============================================================================
# JSON frame parsing property tests
# ============================================================================


class TestJSONFrameParsingProperties:
    """Property tests for JSON frame parsing."""

    @given(
        msg_type=st.sampled_from(
            ["HELLO", "RUN_GQL", "PULL", "BEGIN", "COMMIT", "ROLLBACK"]
        ),
        request_id=st.integers(min_value=0, max_value=2**31 - 1),
    )
    @settings(max_examples=100)
    def test_json_message_roundtrip(self, msg_type, request_id):
        """JSON messages should serialize and deserialize correctly."""
        msg = {"type": msg_type, "request_id": request_id}
        serialized = json.dumps(msg)
        parsed = json.loads(serialized)
        assert parsed["type"] == msg_type
        assert parsed["request_id"] == request_id

    @given(
        query=st.text(max_size=500),
        params=st.dictionaries(
            keys=param_names,
            values=st.one_of(
                st.none(),
                st.booleans(),
                st.integers(min_value=-(2**31), max_value=2**31 - 1),
                st.text(max_size=50),
            ),
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_run_gql_message_roundtrip(self, query, params):
        """RUN_GQL messages should serialize correctly."""
        msg = {"type": "RUN_GQL", "text": query, "params": params}
        serialized = json.dumps(msg)
        parsed = json.loads(serialized)
        assert parsed["text"] == query
        assert parsed["params"] == params

    @given(
        rows=st.lists(
            st.dictionaries(
                keys=identifiers,
                values=st.one_of(st.none(), st.integers(), st.text(max_size=20)),
                max_size=5,
            ),
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_bindings_response_roundtrip(self, rows):
        """BINDINGS responses should serialize correctly."""
        msg = {"result": {"type": "BINDINGS", "rows": rows, "final": True}}
        serialized = json.dumps(msg)
        parsed = json.loads(serialized)
        assert parsed["result"]["rows"] == rows

    @given(arbitrary_bytes=st.binary(max_size=1000))
    @settings(max_examples=100)
    def test_arbitrary_bytes_json_parse_safety(self, arbitrary_bytes):
        """Arbitrary bytes should not crash JSON parser when decoded as UTF-8."""
        try:
            text = arbitrary_bytes.decode("utf-8", errors="replace")
            json.loads(text)
        except json.JSONDecodeError:
            # This is expected for most arbitrary input
            pass


# ============================================================================
# Query builder property tests
# ============================================================================


class TestQueryBuilderProperties:
    """Property tests for QueryBuilder."""

    @given(pattern=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_match_accepts_any_pattern(self, pattern):
        """MATCH should accept any pattern string without crashing."""
        qb = QueryBuilder().match(pattern)
        query, params = qb.build()
        assert pattern in query

    @given(expr=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_where_accepts_any_condition(self, expr):
        """WHERE should accept any condition string without crashing."""
        qb = QueryBuilder().match("(n)").where(expr)
        query, params = qb.build()
        assert expr in query

    @given(
        expressions=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5)
    )
    @settings(max_examples=100)
    def test_return_accepts_multiple_expressions(self, expressions):
        """RETURN should accept multiple expressions."""
        qb = QueryBuilder().return_(*expressions)
        query, params = qb.build()
        for expr in expressions:
            assert expr in query

    @given(n=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=100)
    def test_limit_accepts_valid_integers(self, n):
        """LIMIT should accept non-negative integers."""
        qb = QueryBuilder().return_("n").limit(n)
        query, params = qb.build()
        assert f"LIMIT {n}" in query

    @given(n=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=100)
    def test_offset_accepts_valid_integers(self, n):
        """OFFSET should accept non-negative integers."""
        qb = QueryBuilder().return_("n").offset(n)
        query, params = qb.build()
        assert f"OFFSET {n}" in query

    @given(
        param_name=param_names,
        param_value=st.one_of(
            st.none(), st.booleans(), st.integers(), st.text(max_size=50)
        ),
    )
    @settings(max_examples=100)
    def test_with_param_stores_params(self, param_name, param_value):
        """Parameters should be stored correctly."""
        qb = QueryBuilder().return_("n").with_param(param_name, param_value)
        query, params = qb.build()
        assert param_name in params
        assert params[param_name] == param_value

    @given(
        params=st.dictionaries(
            keys=param_names,
            values=st.one_of(
                st.none(), st.booleans(), st.integers(), st.text(max_size=50)
            ),
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_with_params_stores_all(self, params):
        """Multiple parameters should be stored correctly."""
        qb = QueryBuilder().return_("n").with_params(params)
        query, built_params = qb.build()
        for key, value in params.items():
            assert key in built_params
            assert built_params[key] == value


class TestPatternBuilderProperties:
    """Property tests for PatternBuilder."""

    @given(var=identifiers)
    @settings(max_examples=100)
    def test_node_with_variable(self, var):
        """Node patterns should include variable names."""
        pb = PatternBuilder().node(var)
        pattern = pb.build()
        assert var in pattern

    @given(var=identifiers, label=labels)
    @settings(max_examples=100)
    def test_node_with_label(self, var, label):
        """Node patterns should include labels."""
        pb = PatternBuilder().node(var, label)
        pattern = pb.build()
        assert var in pattern
        assert label in pattern

    @given(
        var=identifiers,
        label=labels,
        props=st.dictionaries(
            keys=identifiers,
            values=st.one_of(
                st.integers(min_value=-100, max_value=100), st.text(max_size=20)
            ),
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_node_with_properties(self, var, label, props):
        """Node patterns should include properties."""
        pb = PatternBuilder().node(var, label, props)
        pattern = pb.build()
        assert var in pattern
        assert label in pattern

    @given(
        var=identifiers,
        rel_type=st.from_regex(r"[A-Z][A-Z0-9_]{0,20}", fullmatch=True),
        direction=st.sampled_from(
            [EdgeDirection.OUTGOING, EdgeDirection.INCOMING, EdgeDirection.UNDIRECTED]
        ),
    )
    @settings(max_examples=100)
    def test_edge_with_type(self, var, rel_type, direction):
        """Edge patterns should include type and direction."""
        pb = PatternBuilder().node("a").edge(var, rel_type, direction).node("b")
        pattern = pb.build()
        assert rel_type in pattern


class TestPredicateBuilderProperties:
    """Property tests for PredicateBuilder."""

    @given(left=identifiers, right=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_equals_predicate(self, left, right):
        """Equals predicate should be built correctly."""
        pb = PredicateBuilder().equals(left, right)
        result = pb.build_and()
        assert left in result
        assert "=" in result

    @given(left=identifiers, right=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_not_equals_predicate(self, left, right):
        """Not equals predicate should be built correctly."""
        pb = PredicateBuilder().not_equals(left, right)
        result = pb.build_and()
        assert left in result
        assert "<>" in result

    @given(left=identifiers, right=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_greater_than_predicate(self, left, right):
        """Greater than predicate should be built correctly."""
        pb = PredicateBuilder().greater_than(left, right)
        result = pb.build_and()
        assert left in result
        assert ">" in result

    @given(left=identifiers, right=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_less_than_predicate(self, left, right):
        """Less than predicate should be built correctly."""
        pb = PredicateBuilder().less_than(left, right)
        result = pb.build_and()
        assert left in result
        assert "<" in result

    @given(field=identifiers)
    @settings(max_examples=100)
    def test_is_null_predicate(self, field):
        """IS NULL predicate should be built correctly."""
        pb = PredicateBuilder().is_null(field)
        result = pb.build_and()
        assert field in result
        assert "IS NULL" in result

    @given(field=identifiers)
    @settings(max_examples=100)
    def test_is_not_null_predicate(self, field):
        """IS NOT NULL predicate should be built correctly."""
        pb = PredicateBuilder().is_not_null(field)
        result = pb.build_and()
        assert field in result
        assert "IS NOT NULL" in result

    @given(
        field=identifiers,
        values=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    def test_in_predicate(self, field, values):
        """IN predicate should be built correctly."""
        pb = PredicateBuilder().in_(field, values)
        result = pb.build_and()
        assert field in result
        assert "IN" in result


# ============================================================================
# Pool configuration property tests
# ============================================================================


class TestPoolConfigProperties:
    """Property tests for ConnectionPool configuration."""

    @given(
        min_size=st.integers(min_value=1, max_value=10),
        max_size=st.integers(min_value=10, max_value=100),
    )
    @settings(max_examples=100)
    def test_pool_size_config(self, min_size, max_size):
        """Pool should accept valid size configuration."""
        assume(min_size <= max_size)
        pool = ConnectionPool(min_size=min_size, max_size=max_size)
        assert pool.min_size == min_size
        assert pool.max_size == max_size

    @given(timeout=st.floats(min_value=0.1, max_value=300.0))
    @settings(max_examples=100)
    def test_pool_timeout_config(self, timeout):
        """Pool should accept valid timeout configuration."""
        pool = ConnectionPool(timeout=timeout)
        assert pool.timeout == timeout


# ============================================================================
# Fuzz-like tests with truly arbitrary input
# ============================================================================


class TestFuzzLikeProperties:
    """Fuzz-like tests that throw arbitrary data at the API."""

    @given(data=st.binary(max_size=500))
    @settings(max_examples=200)
    def test_decode_value_arbitrary_bytes(self, data):
        """decode_value should handle arbitrary byte sequences gracefully."""
        try:
            text = data.decode("utf-8", errors="replace")
            result = decode_value(text, "STRING")
            assert result.kind == ValueKind.STRING
        except (ValueError, TypeError, UnicodeDecodeError):
            # These are acceptable failures
            pass

    @given(data=st.text(max_size=200))
    @settings(max_examples=200)
    def test_decode_value_arbitrary_type(self, data):
        """decode_value should handle arbitrary type names gracefully."""
        try:
            result = decode_value("test", data)
            # Should return some Value
            assert isinstance(result, Value)
        except (ValueError, TypeError, KeyError):
            # These are acceptable failures
            pass

    @given(
        clauses=st.lists(
            st.tuples(
                st.sampled_from(["MATCH", "WHERE", "RETURN", "ORDER BY", "LIMIT"]),
                st.text(max_size=50),
            ),
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_query_builder_arbitrary_clauses(self, clauses):
        """QueryBuilder should handle arbitrary clause sequences."""
        qb = QueryBuilder()
        for clause_type, content in clauses:
            if clause_type == "MATCH":
                qb.match(content)
            elif clause_type == "WHERE":
                qb.where(content)
            elif clause_type == "RETURN":
                qb.return_(content)
            elif clause_type == "ORDER BY":
                qb.order_by(content)
            elif clause_type == "LIMIT":
                try:
                    qb.limit(int(content) if content.isdigit() else 10)
                except (ValueError, OverflowError):
                    qb.limit(10)

        # Should always be able to build
        query, params = qb.build()
        assert isinstance(query, str)
        assert isinstance(params, dict)

    @given(
        nodes=st.lists(
            st.tuples(identifiers, st.one_of(st.none(), labels)), min_size=1, max_size=5
        ),
        edges=st.lists(
            st.tuples(
                identifiers,
                st.from_regex(r"[A-Z][A-Z0-9_]{0,10}", fullmatch=True),
                st.sampled_from(
                    [
                        EdgeDirection.OUTGOING,
                        EdgeDirection.INCOMING,
                        EdgeDirection.UNDIRECTED,
                    ]
                ),
            ),
            max_size=4,
        ),
    )
    @settings(max_examples=100)
    def test_pattern_builder_arbitrary_structure(self, nodes, edges):
        """PatternBuilder should handle arbitrary node/edge sequences."""
        pb = PatternBuilder()

        for i, (var, label) in enumerate(nodes):
            if label:
                pb.node(var, label)
            else:
                pb.node(var)

            if i < len(edges):
                edge_var, edge_type, direction = edges[i]
                pb.edge(edge_var, edge_type, direction)

        # Should always be able to build
        pattern = pb.build()
        assert isinstance(pattern, str)


class TestFormatDSNRoundTrip:
    """format_dsn(parse_dsn(...)) preserves core fields."""

    @given(
        host=st.from_regex(r"[a-z][a-z0-9.\-]{0,20}", fullmatch=True),
        port=ports,
        graph=st.from_regex(r"[a-zA-Z0-9_\-]{0,20}", fullmatch=True),
        tenant=st.from_regex(r"[a-zA-Z0-9_\-]{0,20}", fullmatch=True),
        role=st.from_regex(r"[a-zA-Z0-9_\-]{0,20}", fullmatch=True),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_round_trip_preserves_fields(self, host, port, graph, tenant, role):
        from geode_client import format_dsn, parse_dsn
        from geode_client.transport import TransportConfig, TransportType

        cfg = TransportConfig(
            transport_type=TransportType.QUIC,
            host=host,
            port=port,
            graph=graph,
            tenant=tenant,
            role=role,
        )
        cfg2 = parse_dsn(format_dsn(cfg))
        assert cfg2.host == ("127.0.0.1" if host == "localhost" else host)
        assert cfg2.port == port
        assert cfg2.graph == graph
        assert cfg2.tenant == tenant
        assert cfg2.role == role

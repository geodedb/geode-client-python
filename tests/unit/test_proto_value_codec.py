"""Unit tests for the protobuf <-> Python value codec on Connection.

These tests deliberately use REAL generated protobuf messages
(``geode_client.proto``) rather than ``MagicMock`` objects with
``HasField`` side effects.  A mock only answers ``HasField`` for the arm
the test author remembered, so a missing ``oneof`` arm in the decoder is
invisible.  With real messages, an unhandled arm falls through to the
terminal ``else`` and is observable.

Covers:

* ENG-3909 -- ``Connection._proto_value_to_python`` did not handle the
  ``decimal_val`` arm (``Value.kind`` field 6), so every FLOAT-typed
  expression result from the engine (float literals, arithmetic,
  ``sqrt()``, ``vector_cosine()``, ``CAST(... AS DECIMAL)``) silently
  decoded as NULL, and embeddings decoded as ``[None, None, ...]``.
  ``geode_client.types._DECODERS`` likewise had no FLOAT/DOUBLE/REAL/
  NUMERIC entries, so ``decode_value("1.5", "FLOAT")`` produced a STRING.

* ENG-3910 -- ``Connection._python_to_proto_value`` had no list/dict arm,
  so a list parameter was sent as ``string_val`` holding the Python repr
  (``"['a.md', 'b.md']"``).  That makes ``WHERE NOT d.source IN $blocked``
  fail open and return rows that should have been filtered out.
"""

from decimal import Decimal

import pytest

from geode_client.client import Connection
from geode_client.proto import (
    BytesValue,
    DecimalValue,
    DoubleValue,
    EdgeValue,
    ExtendedValue,
    IntKind,
    IntValue,
    ListValue,
    MapEntry,
    MapValue,
    NodeValue,
    NullValue,
    PathValue,
    StringKind,
    StringValue,
)
from geode_client.proto import Value as ProtoValue
from geode_client.types import ValueKind, decode_value


@pytest.fixture
def conn():
    """A bare Connection -- the codec helpers need no transport."""
    return Connection()


def _decimal(coeff: str, scale: int, orig_scale: int = 0, orig_repr: str = ""):
    """Build a real ``Value`` carrying the ``decimal_val`` oneof arm."""
    return ProtoValue(
        decimal_val=DecimalValue(
            coeff=coeff,
            scale=scale,
            orig_scale=orig_scale,
            orig_repr=orig_repr,
        )
    )


# --------------------------------------------------------------------------
# ENG-3909: decimal_val decoding
# --------------------------------------------------------------------------


class TestDecimalValDecode:
    """ENG-3909: ``Value.decimal_val`` must decode to a DECIMAL, not NULL."""

    def test_decimal_val_decodes_to_decimal_regression(self, conn):
        """ENG-3909 regression: ``RETURN 1.5`` arrives as decimal_val.

        The engine sends FLOAT-typed expression results as
        ``decimal_val {coeff: "15", scale: 1, orig_repr: "1.5"}``.  Before
        the fix the decoder had no ``decimal_val`` arm and the terminal
        ``else`` fabricated ``Value(NULL)``.
        """
        proto = _decimal(coeff="15", scale=1, orig_scale=1, orig_repr="1.5")

        # Sanity: the message really is on the decimal_val arm.
        assert proto.WhichOneof("kind") == "decimal_val"

        result = conn._proto_value_to_python(proto, "FLOAT")

        assert result.kind is not ValueKind.NULL, (
            "decimal_val decoded as NULL -- the decoder is missing the "
            "decimal_val oneof arm (ENG-3909)"
        )
        assert result.kind is ValueKind.DECIMAL
        assert result.as_decimal == Decimal("1.5")

    def test_decimal_val_prefers_orig_repr_over_coeff_scale(self, conn):
        """orig_repr wins when present, preserving the original scale.

        Mirrors the Go client (geode-client-go/rows.go:194-195).  Here
        coeff/scale normalises to ``1.5`` but the engine's original
        rendering was ``1.500``; the client must keep ``1.500``.
        """
        proto = _decimal(coeff="15", scale=1, orig_scale=3, orig_repr="1.500")

        result = conn._proto_value_to_python(proto, "DECIMAL")

        assert result.kind is ValueKind.DECIMAL
        assert result.as_decimal == Decimal("1.500")
        assert str(result.as_decimal) == "1.500", (
            "orig_repr should be used verbatim so the original scale survives"
        )

    def test_decimal_val_falls_back_to_coeff_and_scale(self, conn):
        """With orig_repr empty, value is ``Decimal(coeff).scaleb(-scale)``."""
        proto = _decimal(coeff="12345", scale=2, orig_scale=2, orig_repr="")

        result = conn._proto_value_to_python(proto, "DECIMAL")

        assert result.kind is ValueKind.DECIMAL
        assert result.as_decimal == Decimal("123.45")

    def test_decimal_val_negative_coefficient(self, conn):
        """Negative coefficients keep their sign through coeff/scale math."""
        proto = _decimal(coeff="-15", scale=1)

        result = conn._proto_value_to_python(proto, "DECIMAL")

        assert result.kind is ValueKind.DECIMAL
        assert result.as_decimal == Decimal("-1.5")

    def test_decimal_val_zero_scale_is_integral(self, conn):
        """scale == 0 means the coefficient is the value."""
        proto = _decimal(coeff="42", scale=0)

        result = conn._proto_value_to_python(proto, "DECIMAL")

        assert result.kind is ValueKind.DECIMAL
        assert result.as_decimal == Decimal("42")

    def test_decimal_val_i128_coefficient_is_exact(self, conn):
        """coeff is an i128 decimal string -- must not round-trip via float."""
        coeff = "170141183460469231731687303715884105727"  # i128 max
        proto = _decimal(coeff=coeff, scale=0)

        result = conn._proto_value_to_python(proto, "DECIMAL")

        assert result.kind is ValueKind.DECIMAL
        assert result.as_decimal == Decimal(coeff)

    def test_decimal_val_zero(self, conn):
        """Zero is a value, not an absent field: must not decode as NULL."""
        proto = _decimal(coeff="0", scale=0)

        result = conn._proto_value_to_python(proto, "DECIMAL")

        assert result.kind is ValueKind.DECIMAL
        assert result.as_decimal == Decimal("0")

    def test_embedding_list_of_decimals_has_no_none_elements(self, conn):
        """ENG-3909: an embedding decoded as ``[None, None, ...]``.

        A vector literal arrives as ``list_val`` whose elements are all
        ``decimal_val``.  Every element must decode to a real number.
        """
        proto = ProtoValue(
            list_val=ListValue(
                values=[
                    _decimal(coeff="10", scale=2, orig_scale=2, orig_repr="0.10"),
                    _decimal(coeff="-25", scale=2, orig_scale=2, orig_repr="-0.25"),
                    _decimal(coeff="99", scale=2, orig_scale=2, orig_repr="0.99"),
                ]
            )
        )

        result = conn._proto_value_to_python(proto, "FLOAT[]")

        assert result.kind is ValueKind.ARRAY
        elements = result.as_array
        assert len(elements) == 3
        assert [e.kind for e in elements] == [ValueKind.DECIMAL] * 3, (
            "embedding elements decoded as NULL (ENG-3909)"
        )
        assert [e.as_decimal for e in elements] == [
            Decimal("0.10"),
            Decimal("-0.25"),
            Decimal("0.99"),
        ]

    def test_decimal_val_inside_node_properties(self, conn):
        """A FLOAT node property must survive nested decoding too."""
        proto = ProtoValue(
            node_val=NodeValue(
                id=7,
                labels=["Doc"],
                properties=[
                    MapEntry(
                        key="score",
                        value=_decimal(
                            coeff="875", scale=3, orig_scale=3, orig_repr="0.875"
                        ),
                    )
                ],
            )
        )

        result = conn._proto_value_to_python(proto, "NODE")

        score = result.as_object["properties"].as_object["score"]
        assert score.kind is ValueKind.DECIMAL
        assert score.as_decimal == Decimal("0.875")


# --------------------------------------------------------------------------
# ENG-3909 guard: every oneof arm must be handled
# --------------------------------------------------------------------------


def _sample_for_arm(arm: str) -> ProtoValue:
    """Build a real, populated ``Value`` for the given ``kind`` oneof arm."""
    samples = {
        "null_val": ProtoValue(null_val=NullValue()),
        "int_val": ProtoValue(int_val=IntValue(value=42, kind=IntKind.INT)),
        "double_val": ProtoValue(double_val=DoubleValue(value=3.5)),
        "bool_val": ProtoValue(bool_val=True),
        "string_val": ProtoValue(
            string_val=StringValue(value="hello", kind=StringKind.STRING)
        ),
        "decimal_val": _decimal(coeff="15", scale=1, orig_scale=1, orig_repr="1.5"),
        "bytes_val": ProtoValue(bytes_val=BytesValue(value=b"\x01\x02")),
        "list_val": ProtoValue(
            list_val=ListValue(
                values=[ProtoValue(int_val=IntValue(value=1, kind=IntKind.INT))]
            )
        ),
        "map_val": ProtoValue(
            map_val=MapValue(
                entries=[
                    MapEntry(
                        key="k",
                        value=ProtoValue(int_val=IntValue(value=1, kind=IntKind.INT)),
                    )
                ]
            )
        ),
        "node_val": ProtoValue(node_val=NodeValue(id=1, labels=["N"])),
        "edge_val": ProtoValue(
            edge_val=EdgeValue(id=1, from_id=1, to_id=2, label="REL")
        ),
        "path_val": ProtoValue(
            path_val=PathValue(
                nodes=[NodeValue(id=1, labels=["N"]), NodeValue(id=2, labels=["N"])],
                edges=[EdgeValue(id=1, from_id=1, to_id=2, label="REL")],
            )
        ),
        "ext_val": ProtoValue(
            ext_val=ExtendedValue(type_name="geometry", text="POINT(0 0)")
        ),
    }
    return samples[arm]


ONEOF_ARMS = [f.name for f in ProtoValue.DESCRIPTOR.oneofs_by_name["kind"].fields]


class TestOneofArmCoverage:
    """Guard: no ``Value.kind`` arm may fall through to the NULL default."""

    def test_sample_builder_covers_every_declared_arm(self):
        """If the proto gains a new arm, this test fails first.

        Keeps ``_sample_for_arm`` (and therefore the sweep below) honest
        as ``Value.kind`` evolves.
        """
        assert sorted(ONEOF_ARMS) == sorted(
            [
                "null_val",
                "int_val",
                "double_val",
                "bool_val",
                "string_val",
                "decimal_val",
                "bytes_val",
                "list_val",
                "map_val",
                "node_val",
                "edge_val",
                "path_val",
                "ext_val",
            ]
        ), "Value.kind gained/lost an arm -- update _sample_for_arm and the decoder"

    @pytest.mark.parametrize("arm", ONEOF_ARMS)
    def test_populated_arm_does_not_decode_as_null(self, conn, arm):
        """ENG-3909: only ``null_val`` may decode to NULL.

        Any other arm decoding to NULL means the decoder is missing a
        branch and the terminal ``else`` fabricated a NULL.
        """
        proto = _sample_for_arm(arm)
        assert proto.WhichOneof("kind") == arm

        result = conn._proto_value_to_python(proto, "")

        if arm == "null_val":
            assert result.kind is ValueKind.NULL
        else:
            assert result.kind is not ValueKind.NULL, (
                f"oneof arm {arm!r} decoded to NULL -- unhandled branch in "
                "Connection._proto_value_to_python (ENG-3909)"
            )

    @pytest.mark.parametrize(
        "arm,expected_kind",
        [
            ("null_val", ValueKind.NULL),
            ("int_val", ValueKind.INT),
            ("double_val", ValueKind.DECIMAL),
            ("bool_val", ValueKind.BOOL),
            ("string_val", ValueKind.STRING),
            ("decimal_val", ValueKind.DECIMAL),
            ("bytes_val", ValueKind.BYTEA),
            ("list_val", ValueKind.ARRAY),
            ("map_val", ValueKind.OBJECT),
            ("node_val", ValueKind.NODE),
            ("edge_val", ValueKind.EDGE),
            ("path_val", ValueKind.PATH),
            ("ext_val", ValueKind.STRING),
        ],
    )
    def test_arm_maps_to_expected_value_kind(self, conn, arm, expected_kind):
        """Each arm maps to a specific ValueKind, not just 'not NULL'."""
        result = conn._proto_value_to_python(_sample_for_arm(arm), "")
        assert result.kind is expected_kind


# --------------------------------------------------------------------------
# ENG-3910: list / dict parameter encoding
# --------------------------------------------------------------------------


class TestPythonToProtoContainers:
    """ENG-3910: containers must be encoded structurally, not stringified."""

    def test_list_param_encodes_as_list_val_regression(self, conn):
        """ENG-3910 regression: ``$blocked = ["a.md", "b.md"]``.

        Before the fix the list fell into the ``else`` fallback and was
        sent as ``string_val {value: "['a.md', 'b.md']"}``, so
        ``WHERE NOT d.source IN $blocked`` failed open and returned the
        blocked rows.
        """
        proto = conn._python_to_proto_value(["a.md", "b.md"])

        assert proto.WhichOneof("kind") == "list_val", (
            f"list parameter encoded as {proto.WhichOneof('kind')!r} "
            "instead of list_val (ENG-3910)"
        )
        assert len(proto.list_val.values) == 2
        assert [v.WhichOneof("kind") for v in proto.list_val.values] == [
            "string_val",
            "string_val",
        ]
        assert [v.string_val.value for v in proto.list_val.values] == ["a.md", "b.md"]

    def test_list_param_is_not_stringified(self, conn):
        """The Python ``repr`` must never appear on the wire."""
        proto = conn._python_to_proto_value(["a.md", "b.md"])

        assert proto.string_val.value != "['a.md', 'b.md']"
        assert b"['a.md', 'b.md']" not in proto.SerializeToString()

    def test_empty_list_encodes_as_empty_list_val(self, conn):
        """An empty IN-list is still a list, not the string ``"[]"``."""
        proto = conn._python_to_proto_value([])

        assert proto.WhichOneof("kind") == "list_val"
        assert list(proto.list_val.values) == []

    def test_tuple_param_encodes_as_list_val(self, conn):
        """Tuples are sequences too and must encode like lists."""
        proto = conn._python_to_proto_value(("x", "y"))

        assert proto.WhichOneof("kind") == "list_val"
        assert [v.string_val.value for v in proto.list_val.values] == ["x", "y"]

    def test_mixed_scalar_list_recurses_per_element(self, conn):
        """Each element is encoded by the scalar rules, element by element."""
        proto = conn._python_to_proto_value([1, "two", True, None, 3.5])

        assert proto.WhichOneof("kind") == "list_val"
        arms = [v.WhichOneof("kind") for v in proto.list_val.values]
        assert arms == ["int_val", "string_val", "bool_val", "null_val", "double_val"]
        assert proto.list_val.values[0].int_val.value == 1
        assert proto.list_val.values[1].string_val.value == "two"
        assert proto.list_val.values[2].bool_val is True
        assert proto.list_val.values[4].double_val.value == 3.5

    def test_nested_list_encodes_as_nested_list_val(self, conn):
        """Nested lists (e.g. a batch of embeddings) nest structurally."""
        proto = conn._python_to_proto_value([[1, 2], [3]])

        assert proto.WhichOneof("kind") == "list_val"
        outer = list(proto.list_val.values)
        assert [v.WhichOneof("kind") for v in outer] == ["list_val", "list_val"]
        assert [v.int_val.value for v in outer[0].list_val.values] == [1, 2]
        assert [v.int_val.value for v in outer[1].list_val.values] == [3]

    def test_dict_param_encodes_as_map_val(self, conn):
        """ENG-3910: dict parameters must become ``map_val`` entries."""
        proto = conn._python_to_proto_value({"name": "ada", "age": 36})

        assert proto.WhichOneof("kind") == "map_val", (
            f"dict parameter encoded as {proto.WhichOneof('kind')!r} "
            "instead of map_val (ENG-3910)"
        )
        entries = {e.key: e.value for e in proto.map_val.entries}
        assert set(entries) == {"name", "age"}
        assert entries["name"].WhichOneof("kind") == "string_val"
        assert entries["name"].string_val.value == "ada"
        assert entries["age"].WhichOneof("kind") == "int_val"
        assert entries["age"].int_val.value == 36

    def test_dict_containing_list_encodes_structurally(self, conn):
        """Maps and lists compose in both directions."""
        proto = conn._python_to_proto_value({"tags": ["a", "b"]})

        assert proto.WhichOneof("kind") == "map_val"
        entry = proto.map_val.entries[0]
        assert entry.key == "tags"
        assert entry.value.WhichOneof("kind") == "list_val"
        assert [v.string_val.value for v in entry.value.list_val.values] == ["a", "b"]

    def test_string_param_is_not_treated_as_a_sequence(self, conn):
        """Guard: ``str`` is iterable but must stay a scalar string."""
        proto = conn._python_to_proto_value("a.md")

        assert proto.WhichOneof("kind") == "string_val"
        assert proto.string_val.value == "a.md"

    def test_bytes_param_is_not_treated_as_a_sequence(self, conn):
        """Guard: ``bytes`` must not be exploded into a list of ints."""
        proto = conn._python_to_proto_value(b"\x01\x02")

        assert proto.WhichOneof("kind") != "list_val"

    def test_list_param_roundtrips_back_to_python_list(self, conn):
        """End-to-end: encode then decode preserves list semantics.

        This is the property that ``WHERE NOT d.source IN $blocked``
        depends on -- the server must see three distinct strings, not one
        string containing brackets and quotes.
        """
        blocked = ["a.md", "b.md", "c.md"]

        decoded = conn._proto_value_to_python(conn._python_to_proto_value(blocked), "")

        assert decoded.kind is ValueKind.ARRAY
        assert [v.as_string for v in decoded.as_array] == blocked


# --------------------------------------------------------------------------
# ENG-3909: types._DECODERS float-family gap
# --------------------------------------------------------------------------


class TestDecodeValueFloatTypes:
    """ENG-3909: ``decode_value`` had no FLOAT/DOUBLE/REAL/NUMERIC entry."""

    @pytest.mark.parametrize(
        "type_name", ["FLOAT", "float", "DOUBLE", "REAL", "NUMERIC"]
    )
    def test_float_family_decodes_as_decimal_not_string(self, type_name):
        """``decode_value("1.5", "FLOAT")`` produced ``Value(STRING)``."""
        result = decode_value("1.5", type_name)

        assert result.kind is not ValueKind.STRING, (
            f"decode_value with type {type_name!r} produced a STRING -- "
            "types._DECODERS is missing the float family (ENG-3909)"
        )
        assert result.kind is ValueKind.DECIMAL
        assert result.as_decimal == Decimal("1.5")

    def test_float_decode_accepts_native_float(self):
        """Engine JSON may deliver a native float rather than a string."""
        result = decode_value(2.25, "FLOAT")

        assert result.kind is ValueKind.DECIMAL
        assert result.as_decimal == Decimal("2.25")

    def test_float_decode_negative(self):
        """Negative float values keep their sign and DECIMAL kind."""
        result = decode_value("-0.5", "DOUBLE")

        assert result.kind is ValueKind.DECIMAL
        assert result.as_decimal == Decimal("-0.5")

    def test_float_decode_null_still_null(self):
        """A NULL FLOAT column stays NULL (no regression on the null path)."""
        assert decode_value(None, "FLOAT").kind is ValueKind.NULL

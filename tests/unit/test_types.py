"""Unit tests for Geode type system."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from geode_client import Range, Value, ValueKind
from geode_client.types import decode_value


class TestValueKind:
    """Tests for ValueKind enum."""

    def test_all_kinds_exist(self):
        """Test that all expected ValueKind variants exist."""
        expected_kinds = [
            "NULL",
            "INT",
            "BOOL",
            "STRING",
            "DECIMAL",
            "ARRAY",
            "OBJECT",
            "BYTEA",
            "DATE",
            "TIME",
            "TIMETZ",
            "TIMESTAMP",
            "TIMESTAMPTZ",
            "INTERVAL",
            "JSON",
            "JSONB",
            "XML",
            "URL",
            "DOMAIN",
            "UUID",
            "ENUM",
            "BIT_STRING",
            "RANGE",
        ]
        for kind_name in expected_kinds:
            assert hasattr(ValueKind, kind_name), f"Missing ValueKind.{kind_name}"

    def test_kinds_are_unique(self):
        """Test that all ValueKind values are unique."""
        values = [kind.value for kind in ValueKind]
        assert len(values) == len(set(values))

    def test_kind_name(self):
        """Test ValueKind name property."""
        assert ValueKind.NULL.name == "NULL"
        assert ValueKind.INT.name == "INT"
        assert ValueKind.STRING.name == "STRING"


class TestValueConstruction:
    """Tests for Value construction."""

    def test_null_value(self):
        """Test NULL value construction."""
        val = Value(kind=ValueKind.NULL)
        assert val.kind == ValueKind.NULL
        assert val.is_null is True

    def test_int_value(self):
        """Test INT value construction."""
        val = Value(kind=ValueKind.INT, int_value=42)
        assert val.kind == ValueKind.INT
        assert val.int_value == 42
        assert val.is_null is False

    def test_int_negative(self):
        """Test negative INT value."""
        val = Value(kind=ValueKind.INT, int_value=-100)
        assert val.int_value == -100

    def test_int_zero(self):
        """Test zero INT value."""
        val = Value(kind=ValueKind.INT, int_value=0)
        assert val.int_value == 0

    def test_int_large(self):
        """Test large INT value."""
        val = Value(kind=ValueKind.INT, int_value=2**62)
        assert val.int_value == 2**62

    def test_bool_true(self):
        """Test BOOL true value."""
        val = Value(kind=ValueKind.BOOL, bool_value=True)
        assert val.kind == ValueKind.BOOL
        assert val.bool_value is True

    def test_bool_false(self):
        """Test BOOL false value."""
        val = Value(kind=ValueKind.BOOL, bool_value=False)
        assert val.kind == ValueKind.BOOL
        assert val.bool_value is False

    def test_string_value(self):
        """Test STRING value construction."""
        val = Value(kind=ValueKind.STRING, str_value="hello")
        assert val.kind == ValueKind.STRING
        assert val.str_value == "hello"

    def test_string_empty(self):
        """Test empty STRING value."""
        val = Value(kind=ValueKind.STRING, str_value="")
        assert val.str_value == ""

    def test_string_unicode(self):
        """Test STRING with unicode characters."""
        val = Value(kind=ValueKind.STRING, str_value="Hello, World!")
        assert val.str_value == "Hello, World!"

    def test_decimal_value(self):
        """Test DECIMAL value construction."""
        val = Value(kind=ValueKind.DECIMAL, decimal_value=Decimal("123.456"))
        assert val.kind == ValueKind.DECIMAL
        assert val.decimal_value == Decimal("123.456")

    def test_decimal_precision(self):
        """Test DECIMAL preserves precision."""
        val = Value(
            kind=ValueKind.DECIMAL,
            decimal_value=Decimal("0.123456789012345678901234567890"),
        )
        assert str(val.decimal_value) == "0.123456789012345678901234567890"

    def test_array_value(self):
        """Test ARRAY value construction."""
        items = [
            Value(kind=ValueKind.INT, int_value=1),
            Value(kind=ValueKind.INT, int_value=2),
            Value(kind=ValueKind.INT, int_value=3),
        ]
        val = Value(kind=ValueKind.ARRAY, array_value=items)
        assert val.kind == ValueKind.ARRAY
        assert len(val.array_value) == 3

    def test_array_empty(self):
        """Test empty ARRAY value."""
        val = Value(kind=ValueKind.ARRAY, array_value=[])
        assert len(val.array_value) == 0

    def test_array_default_init(self):
        """Test ARRAY default initialization."""
        val = Value(kind=ValueKind.ARRAY)
        assert val.array_value == []

    def test_object_value(self):
        """Test OBJECT value construction."""
        fields = {
            "name": Value(kind=ValueKind.STRING, str_value="Alice"),
            "age": Value(kind=ValueKind.INT, int_value=30),
        }
        val = Value(kind=ValueKind.OBJECT, object_value=fields)
        assert val.kind == ValueKind.OBJECT
        assert len(val.object_value) == 2

    def test_object_empty(self):
        """Test empty OBJECT value."""
        val = Value(kind=ValueKind.OBJECT, object_value={})
        assert len(val.object_value) == 0

    def test_object_default_init(self):
        """Test OBJECT default initialization."""
        val = Value(kind=ValueKind.OBJECT)
        assert val.object_value == {}

    def test_bytea_value(self):
        """Test BYTEA value construction."""
        val = Value(kind=ValueKind.BYTEA, bytes_value=b"\x00\x01\x02\x03")
        assert val.kind == ValueKind.BYTEA
        assert val.bytes_value == b"\x00\x01\x02\x03"

    def test_date_value(self):
        """Test DATE value construction."""
        d = date(2024, 1, 15)
        val = Value(kind=ValueKind.DATE, time_value=d)
        assert val.kind == ValueKind.DATE
        assert val.time_value == d

    def test_timestamp_value(self):
        """Test TIMESTAMP value construction."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        val = Value(kind=ValueKind.TIMESTAMP, time_value=dt)
        assert val.kind == ValueKind.TIMESTAMP
        assert val.time_value == dt

    def test_range_value(self):
        """Test RANGE value construction."""
        r = Range(
            lower=Value(kind=ValueKind.INT, int_value=1),
            upper=Value(kind=ValueKind.INT, int_value=10),
            bounds="[)",
        )
        val = Value(kind=ValueKind.RANGE, range_value=r)
        assert val.kind == ValueKind.RANGE
        assert val.range_value.bounds == "[)"


class TestValueAccessors:
    """Tests for Value type-safe accessors."""

    def test_as_int(self):
        """Test as_int accessor."""
        val = Value(kind=ValueKind.INT, int_value=42)
        assert val.as_int == 42

    def test_as_int_wrong_type(self):
        """Test as_int raises for wrong type."""
        val = Value(kind=ValueKind.STRING, str_value="hello")
        with pytest.raises(ValueError, match="Cannot convert"):
            _ = val.as_int

    def test_as_bool(self):
        """Test as_bool accessor."""
        val = Value(kind=ValueKind.BOOL, bool_value=True)
        assert val.as_bool is True

    def test_as_bool_wrong_type(self):
        """Test as_bool raises for wrong type."""
        val = Value(kind=ValueKind.INT, int_value=1)
        with pytest.raises(ValueError, match="Cannot convert"):
            _ = val.as_bool

    def test_as_string(self):
        """Test as_string accessor."""
        val = Value(kind=ValueKind.STRING, str_value="hello")
        assert val.as_string == "hello"

    def test_as_string_from_int(self):
        """Test as_string from INT value."""
        val = Value(kind=ValueKind.INT, int_value=42)
        assert val.as_string == "42"

    def test_as_string_from_bool(self):
        """Test as_string from BOOL value."""
        val = Value(kind=ValueKind.BOOL, bool_value=True)
        assert val.as_string == "True"

    def test_as_string_from_decimal(self):
        """Test as_string from DECIMAL value."""
        val = Value(kind=ValueKind.DECIMAL, decimal_value=Decimal("123.45"))
        assert val.as_string == "123.45"

    def test_as_decimal(self):
        """Test as_decimal accessor."""
        val = Value(kind=ValueKind.DECIMAL, decimal_value=Decimal("3.14"))
        assert val.as_decimal == Decimal("3.14")

    def test_as_decimal_wrong_type(self):
        """Test as_decimal raises for wrong type."""
        val = Value(kind=ValueKind.INT, int_value=42)
        with pytest.raises(ValueError, match="Cannot convert"):
            _ = val.as_decimal

    def test_as_array(self):
        """Test as_array accessor."""
        items = [Value(kind=ValueKind.INT, int_value=1)]
        val = Value(kind=ValueKind.ARRAY, array_value=items)
        assert val.as_array == items

    def test_as_array_wrong_type(self):
        """Test as_array raises for wrong type."""
        val = Value(kind=ValueKind.STRING, str_value="hello")
        with pytest.raises(ValueError, match="Cannot convert"):
            _ = val.as_array

    def test_as_object(self):
        """Test as_object accessor."""
        fields = {"key": Value(kind=ValueKind.STRING, str_value="value")}
        val = Value(kind=ValueKind.OBJECT, object_value=fields)
        assert val.as_object == fields

    def test_as_object_wrong_type(self):
        """Test as_object raises for wrong type."""
        val = Value(kind=ValueKind.ARRAY, array_value=[])
        with pytest.raises(ValueError, match="Cannot convert"):
            _ = val.as_object

    def test_as_bytes(self):
        """Test as_bytes accessor."""
        val = Value(kind=ValueKind.BYTEA, bytes_value=b"\x01\x02")
        assert val.as_bytes == b"\x01\x02"

    def test_as_bytes_wrong_type(self):
        """Test as_bytes raises for wrong type."""
        val = Value(kind=ValueKind.STRING, str_value="hello")
        with pytest.raises(ValueError, match="Cannot convert"):
            _ = val.as_bytes

    def test_as_datetime(self):
        """Test as_datetime accessor."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        val = Value(kind=ValueKind.TIMESTAMP, time_value=dt)
        assert val.as_datetime == dt

    def test_as_datetime_from_timestamptz(self):
        """Test as_datetime from TIMESTAMPTZ."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        val = Value(kind=ValueKind.TIMESTAMPTZ, time_value=dt)
        assert val.as_datetime == dt

    def test_as_datetime_wrong_type(self):
        """Test as_datetime raises for wrong type."""
        val = Value(kind=ValueKind.DATE, time_value=date(2024, 1, 15))
        with pytest.raises(ValueError, match="Cannot convert"):
            _ = val.as_datetime

    def test_as_date(self):
        """Test as_date accessor."""
        d = date(2024, 1, 15)
        val = Value(kind=ValueKind.DATE, time_value=d)
        assert val.as_date == d

    def test_as_date_wrong_type(self):
        """Test as_date raises for wrong type."""
        val = Value(kind=ValueKind.STRING, str_value="2024-01-15")
        with pytest.raises(ValueError, match="Cannot convert"):
            _ = val.as_date

    def test_as_range(self):
        """Test as_range accessor."""
        r = Range(bounds="[]")
        val = Value(kind=ValueKind.RANGE, range_value=r)
        assert val.as_range == r

    def test_as_range_wrong_type(self):
        """Test as_range raises for wrong type."""
        val = Value(kind=ValueKind.INT, int_value=42)
        with pytest.raises(ValueError, match="Cannot convert"):
            _ = val.as_range


class TestValueRawValue:
    """Tests for Value.raw_value property."""

    def test_raw_null(self):
        """Test raw_value for NULL."""
        val = Value(kind=ValueKind.NULL)
        assert val.raw_value is None

    def test_raw_int(self):
        """Test raw_value for INT."""
        val = Value(kind=ValueKind.INT, int_value=42)
        assert val.raw_value == 42
        assert isinstance(val.raw_value, int)

    def test_raw_bool(self):
        """Test raw_value for BOOL."""
        val = Value(kind=ValueKind.BOOL, bool_value=True)
        assert val.raw_value is True

    def test_raw_string(self):
        """Test raw_value for STRING."""
        val = Value(kind=ValueKind.STRING, str_value="hello")
        assert val.raw_value == "hello"

    def test_raw_decimal(self):
        """Test raw_value for DECIMAL."""
        val = Value(kind=ValueKind.DECIMAL, decimal_value=Decimal("3.14"))
        assert val.raw_value == Decimal("3.14")

    def test_raw_array(self):
        """Test raw_value for ARRAY."""
        items = [
            Value(kind=ValueKind.INT, int_value=1),
            Value(kind=ValueKind.INT, int_value=2),
        ]
        val = Value(kind=ValueKind.ARRAY, array_value=items)
        assert val.raw_value == [1, 2]

    def test_raw_object(self):
        """Test raw_value for OBJECT."""
        fields = {
            "name": Value(kind=ValueKind.STRING, str_value="Alice"),
            "age": Value(kind=ValueKind.INT, int_value=30),
        }
        val = Value(kind=ValueKind.OBJECT, object_value=fields)
        assert val.raw_value == {"name": "Alice", "age": 30}

    def test_raw_bytea(self):
        """Test raw_value for BYTEA."""
        val = Value(kind=ValueKind.BYTEA, bytes_value=b"\x01\x02")
        assert val.raw_value == b"\x01\x02"

    def test_raw_date(self):
        """Test raw_value for DATE."""
        d = date(2024, 1, 15)
        val = Value(kind=ValueKind.DATE, time_value=d)
        assert val.raw_value == d

    def test_raw_timestamp(self):
        """Test raw_value for TIMESTAMP."""
        dt = datetime(2024, 1, 15, 10, 30)
        val = Value(kind=ValueKind.TIMESTAMP, time_value=dt)
        assert val.raw_value == dt

    def test_raw_range(self):
        """Test raw_value for RANGE."""
        r = Range(bounds="[]")
        val = Value(kind=ValueKind.RANGE, range_value=r)
        assert val.raw_value == r


class TestDecodeValue:
    """Tests for decode_value function."""

    def test_decode_null(self):
        """Test decoding None to NULL."""
        val = decode_value(None, "STRING")
        assert val.kind == ValueKind.NULL
        assert val.is_null

    def test_decode_int(self):
        """Test decoding INT type."""
        val = decode_value(42, "INT")
        assert val.kind == ValueKind.INT
        assert val.int_value == 42

    def test_decode_int_from_string(self):
        """Test decoding INT from string representation."""
        val = decode_value("42", "INT")
        assert val.kind == ValueKind.INT
        assert val.int_value == 42

    def test_decode_bool_true(self):
        """Test decoding BOOL true."""
        val = decode_value(True, "BOOL")
        assert val.kind == ValueKind.BOOL
        assert val.bool_value is True

    def test_decode_bool_false(self):
        """Test decoding BOOL false."""
        val = decode_value(False, "BOOL")
        assert val.kind == ValueKind.BOOL
        assert val.bool_value is False

    def test_decode_string(self):
        """Test decoding STRING type."""
        val = decode_value("hello", "STRING")
        assert val.kind == ValueKind.STRING
        assert val.str_value == "hello"

    def test_decode_decimal(self):
        """Test decoding DECIMAL type."""
        val = decode_value("123.456", "DECIMAL")
        assert val.kind == ValueKind.DECIMAL
        assert val.decimal_value == Decimal("123.456")

    def test_decode_decimal_quoted(self):
        """Test decoding quoted DECIMAL."""
        val = decode_value('"123.456"', "DECIMAL")
        assert val.kind == ValueKind.DECIMAL
        assert val.decimal_value == Decimal("123.456")

    def test_decode_decimal_scale(self):
        """Test decode_value preserves decimal scale."""
        val = decode_value("123.450", "DECIMAL")
        assert val.decimal_scale == "450"

    def test_decode_bytea_hex(self):
        """Test decoding BYTEA from hex string."""
        val = decode_value("\\x0102ff", "BYTEA")
        assert val.kind == ValueKind.BYTEA
        assert val.bytes_value == b"\x01\x02\xff"

    def test_decode_bytea_plain(self):
        """Test decoding BYTEA plain string."""
        val = decode_value("plain", "BYTEA")
        assert val.kind == ValueKind.BYTEA
        assert val.str_value == "plain"

    def test_decode_date(self):
        """Test decoding DATE type."""
        val = decode_value("2024-01-15", "DATE")
        assert val.kind == ValueKind.DATE
        assert val.time_value == date(2024, 1, 15)

    def test_decode_date_invalid(self):
        """Test decoding invalid DATE."""
        val = decode_value("not-a-date", "DATE")
        assert val.kind == ValueKind.DATE
        assert val.str_value == "not-a-date"
        assert val.time_value is None

    def test_decode_timestamp(self):
        """Test decoding TIMESTAMP type."""
        val = decode_value("2024-01-15T10:30:45", "TIMESTAMP")
        assert val.kind == ValueKind.TIMESTAMP
        assert val.time_value == datetime(2024, 1, 15, 10, 30, 45)

    def test_decode_timestamp_with_z(self):
        """Test decoding TIMESTAMP with Z suffix."""
        val = decode_value("2024-01-15T10:30:45Z", "TIMESTAMP")
        assert val.kind == ValueKind.TIMESTAMP
        assert val.time_value is not None

    def test_decode_timestamptz(self):
        """Test decoding TIMESTAMPTZ type."""
        val = decode_value("2024-01-15T10:30:45+00:00", "TIMESTAMPTZ")
        assert val.kind == ValueKind.TIMESTAMPTZ

    def test_decode_time(self):
        """Test decoding TIME type."""
        val = decode_value("10:30:45", "TIME")
        assert val.kind == ValueKind.TIME
        assert val.str_value == "10:30:45"

    def test_decode_timetz(self):
        """Test decoding TIMETZ type."""
        val = decode_value("10:30:45+00:00", "TIMETZ")
        assert val.kind == ValueKind.TIMETZ

    def test_decode_interval(self):
        """Test decoding INTERVAL type."""
        val = decode_value("P1Y2M3D", "INTERVAL")
        assert val.kind == ValueKind.INTERVAL
        assert val.str_value == "P1Y2M3D"

    def test_decode_json(self):
        """Test decoding JSON type."""
        val = decode_value('{"key": "value"}', "JSON")
        assert val.kind == ValueKind.JSON
        assert val.str_value == '{"key": "value"}'

    def test_decode_jsonb(self):
        """Test decoding JSONB type."""
        val = decode_value('{"key": "value"}', "JSONB")
        assert val.kind == ValueKind.JSONB

    def test_decode_xml(self):
        """Test decoding XML type."""
        val = decode_value("<root><child/></root>", "XML")
        assert val.kind == ValueKind.XML
        assert val.str_value == "<root><child/></root>"

    def test_decode_url(self):
        """Test decoding URL type."""
        val = decode_value("https://example.com", "URL")
        assert val.kind == ValueKind.URL
        assert val.str_value == "https://example.com"

    def test_decode_uri(self):
        """Test decoding URI type (alias for URL)."""
        val = decode_value("https://example.com", "URI")
        assert val.kind == ValueKind.URL

    def test_decode_domain(self):
        """Test decoding DOMAIN type."""
        val = decode_value("example.com", "DOMAIN")
        assert val.kind == ValueKind.DOMAIN

    def test_decode_uuid(self):
        """Test decoding UUID type."""
        val = decode_value("550e8400-e29b-41d4-a716-446655440000", "UUID")
        assert val.kind == ValueKind.UUID
        assert val.str_value == "550e8400-e29b-41d4-a716-446655440000"

    def test_decode_enum(self):
        """Test decoding ENUM type."""
        val = decode_value("ACTIVE", "ENUM")
        assert val.kind == ValueKind.ENUM
        assert val.str_value == "ACTIVE"

    def test_decode_bit(self):
        """Test decoding BIT type."""
        val = decode_value("10110", "BIT")
        assert val.kind == ValueKind.BIT_STRING

    def test_decode_varbit(self):
        """Test decoding VARBIT type."""
        val = decode_value("10110", "VARBIT")
        assert val.kind == ValueKind.BIT_STRING

    def test_decode_range_dict(self):
        """Test decoding RANGE from dict."""
        val = decode_value({"lower": 1, "upper": 10, "bounds": "[)"}, "RANGE")
        assert val.kind == ValueKind.RANGE
        assert val.range_value.bounds == "[)"
        assert val.range_value.lower.int_value == 1
        assert val.range_value.upper.int_value == 10

    def test_decode_range_string(self):
        """Test decoding RANGE from string."""
        val = decode_value("[1,10)", "RANGE")
        assert val.kind == ValueKind.RANGE

    def test_decode_array_untyped(self):
        """Test decoding array without explicit type."""
        val = decode_value([1, 2, 3], "")
        assert val.kind == ValueKind.ARRAY
        assert len(val.array_value) == 3
        assert val.array_value[0].int_value == 1

    def test_decode_object_untyped(self):
        """Test decoding object without explicit type."""
        val = decode_value({"name": "Alice", "age": 30}, "")
        assert val.kind == ValueKind.OBJECT
        assert val.object_value["name"].str_value == "Alice"
        assert val.object_value["age"].int_value == 30

    def test_decode_string_untyped(self):
        """Test decoding string without explicit type."""
        val = decode_value("hello", "")
        assert val.kind == ValueKind.STRING
        assert val.str_value == "hello"

    def test_decode_bool_untyped(self):
        """Test decoding bool without explicit type."""
        val = decode_value(True, "")
        assert val.kind == ValueKind.BOOL
        assert val.bool_value is True

    def test_decode_int_untyped(self):
        """Test decoding int without explicit type."""
        val = decode_value(42, "")
        assert val.kind == ValueKind.INT
        assert val.int_value == 42

    def test_decode_float_untyped(self):
        """Test decoding float without explicit type."""
        val = decode_value(3.14, "")
        assert val.kind == ValueKind.DECIMAL
        assert val.decimal_value == Decimal("3.14")


class TestValueRepr:
    """Tests for Value __repr__."""

    def test_repr_null(self):
        """Test repr for NULL value."""
        val = Value(kind=ValueKind.NULL)
        assert repr(val) == "Value(NULL)"

    def test_repr_int(self):
        """Test repr for INT value."""
        val = Value(kind=ValueKind.INT, int_value=42)
        assert repr(val) == "Value(INT: 42)"

    def test_repr_bool(self):
        """Test repr for BOOL value."""
        val = Value(kind=ValueKind.BOOL, bool_value=True)
        assert repr(val) == "Value(BOOL: True)"

    def test_repr_string(self):
        """Test repr for STRING value."""
        val = Value(kind=ValueKind.STRING, str_value="hello")
        assert repr(val) == "Value(STRING: 'hello')"

    def test_repr_decimal(self):
        """Test repr for DECIMAL value."""
        val = Value(kind=ValueKind.DECIMAL, decimal_value=Decimal("3.14"))
        assert repr(val) == "Value(DECIMAL: 3.14)"

    def test_repr_array(self):
        """Test repr for ARRAY value."""
        items = [Value(kind=ValueKind.INT, int_value=i) for i in range(5)]
        val = Value(kind=ValueKind.ARRAY, array_value=items)
        assert repr(val) == "Value(ARRAY: 5 items)"

    def test_repr_object(self):
        """Test repr for OBJECT value."""
        fields = {
            "a": Value(kind=ValueKind.INT, int_value=1),
            "b": Value(kind=ValueKind.INT, int_value=2),
        }
        val = Value(kind=ValueKind.OBJECT, object_value=fields)
        assert repr(val) == "Value(OBJECT: 2 fields)"

    def test_repr_other(self):
        """Test repr for other types."""
        val = Value(kind=ValueKind.UUID, str_value="abc")
        assert "UUID" in repr(val)


class TestRange:
    """Tests for Range dataclass."""

    def test_range_default(self):
        """Test Range default values."""
        r = Range()
        assert r.lower is None
        assert r.upper is None
        assert r.bounds == ""

    def test_range_with_bounds(self):
        """Test Range with all fields."""
        r = Range(
            lower=Value(kind=ValueKind.INT, int_value=1),
            upper=Value(kind=ValueKind.INT, int_value=10),
            bounds="[)",
        )
        assert r.lower.int_value == 1
        assert r.upper.int_value == 10
        assert r.bounds == "[)"

    def test_range_unbounded_lower(self):
        """Test Range with unbounded lower."""
        r = Range(upper=Value(kind=ValueKind.INT, int_value=10), bounds="()")
        assert r.lower is None
        assert r.upper.int_value == 10

    def test_range_unbounded_upper(self):
        """Test Range with unbounded upper."""
        r = Range(lower=Value(kind=ValueKind.INT, int_value=1), bounds="[)")
        assert r.lower.int_value == 1
        assert r.upper is None


class TestNestedValues:
    """Tests for nested Value structures."""

    def test_nested_array(self):
        """Test nested arrays."""
        inner = Value(
            kind=ValueKind.ARRAY,
            array_value=[
                Value(kind=ValueKind.INT, int_value=1),
                Value(kind=ValueKind.INT, int_value=2),
            ],
        )
        outer = Value(kind=ValueKind.ARRAY, array_value=[inner])
        assert outer.array_value[0].array_value[0].int_value == 1

    def test_nested_object(self):
        """Test nested objects."""
        inner = Value(
            kind=ValueKind.OBJECT,
            object_value={"x": Value(kind=ValueKind.INT, int_value=10)},
        )
        outer = Value(kind=ValueKind.OBJECT, object_value={"nested": inner})
        assert outer.object_value["nested"].object_value["x"].int_value == 10

    def test_array_of_objects(self):
        """Test array of objects."""
        obj1 = Value(
            kind=ValueKind.OBJECT,
            object_value={"name": Value(kind=ValueKind.STRING, str_value="Alice")},
        )
        obj2 = Value(
            kind=ValueKind.OBJECT,
            object_value={"name": Value(kind=ValueKind.STRING, str_value="Bob")},
        )
        arr = Value(kind=ValueKind.ARRAY, array_value=[obj1, obj2])
        assert arr.array_value[0].object_value["name"].str_value == "Alice"
        assert arr.array_value[1].object_value["name"].str_value == "Bob"

    def test_decode_nested_structure(self):
        """Test decode_value with nested structure."""
        raw = {
            "users": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            "count": 2,
        }
        val = decode_value(raw, "")
        assert val.kind == ValueKind.OBJECT
        users = val.object_value["users"]
        assert users.kind == ValueKind.ARRAY
        assert len(users.array_value) == 2
        assert users.array_value[0].object_value["name"].str_value == "Alice"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_bool_before_int_decode(self):
        """Test that bool is handled before int in decode_value."""
        # Python's bool is a subclass of int, so this is important
        val_true = decode_value(True, "")
        val_false = decode_value(False, "")
        assert val_true.kind == ValueKind.BOOL
        assert val_false.kind == ValueKind.BOOL
        assert val_true.bool_value is True
        assert val_false.bool_value is False

    def test_type_case_insensitive(self):
        """Test that type names are case insensitive."""
        assert decode_value(42, "int").kind == ValueKind.INT
        assert decode_value(42, "INT").kind == ValueKind.INT
        assert decode_value(42, "Int").kind == ValueKind.INT

    def test_empty_string_is_not_null(self):
        """Test that empty string is STRING, not NULL."""
        val = decode_value("", "STRING")
        assert val.kind == ValueKind.STRING
        assert not val.is_null

    def test_zero_is_not_null(self):
        """Test that zero is INT, not NULL."""
        val = decode_value(0, "INT")
        assert val.kind == ValueKind.INT
        assert not val.is_null

    def test_false_is_not_null(self):
        """Test that false is BOOL, not NULL."""
        val = decode_value(False, "BOOL")
        assert val.kind == ValueKind.BOOL
        assert not val.is_null

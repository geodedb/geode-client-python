"""
Benchmarks for type conversion operations.

Tests the performance of:
- decode_value() for various types
- Value type accessors
- Decimal parsing
- Timestamp parsing
- Array/Object handling
"""

import pytest
from decimal import Decimal
from datetime import datetime, date

from geode_client import Value, ValueKind
from geode_client.types import decode_value


# ============================================================================
# decode_value benchmarks
# ============================================================================

class TestDecodeValueBenchmarks:
    """Benchmarks for decode_value function."""

    def test_decode_null(self, benchmark):
        """Benchmark decoding NULL values."""
        benchmark(decode_value, None, "")

    def test_decode_int_small(self, benchmark):
        """Benchmark decoding small integers."""
        benchmark(decode_value, 42, "INT")

    def test_decode_int_large(self, benchmark):
        """Benchmark decoding large integers."""
        benchmark(decode_value, 9223372036854775807, "INT")

    def test_decode_bool(self, benchmark):
        """Benchmark decoding booleans."""
        benchmark(decode_value, True, "BOOL")

    def test_decode_string_short(self, benchmark):
        """Benchmark decoding short strings."""
        benchmark(decode_value, "hello", "STRING")

    def test_decode_string_long(self, benchmark):
        """Benchmark decoding long strings (1KB)."""
        long_string = "x" * 1024
        benchmark(decode_value, long_string, "STRING")

    def test_decode_decimal(self, benchmark):
        """Benchmark decoding decimal values."""
        benchmark(decode_value, "123.456789012345", "DECIMAL")

    def test_decode_decimal_high_precision(self, benchmark):
        """Benchmark decoding high-precision decimals."""
        benchmark(decode_value, "123.456789012345678901234567890", "DECIMAL")

    def test_decode_date(self, benchmark):
        """Benchmark decoding date values."""
        benchmark(decode_value, "2024-01-15", "DATE")

    def test_decode_timestamp(self, benchmark):
        """Benchmark decoding timestamp values."""
        benchmark(decode_value, "2024-01-15T10:30:45", "TIMESTAMP")

    def test_decode_timestamp_with_tz(self, benchmark):
        """Benchmark decoding timestamp with timezone."""
        benchmark(decode_value, "2024-01-15T10:30:45+00:00", "TIMESTAMPTZ")

    def test_decode_array_small(self, benchmark):
        """Benchmark decoding small arrays."""
        benchmark(decode_value, [1, 2, 3, 4, 5], "")

    def test_decode_array_medium(self, benchmark):
        """Benchmark decoding medium arrays (100 elements)."""
        arr = list(range(100))
        benchmark(decode_value, arr, "")

    def test_decode_array_large(self, benchmark):
        """Benchmark decoding large arrays (1000 elements)."""
        arr = list(range(1000))
        benchmark(decode_value, arr, "")

    def test_decode_object_small(self, benchmark):
        """Benchmark decoding small objects."""
        obj = {"name": "Alice", "age": 30}
        benchmark(decode_value, obj, "")

    def test_decode_object_medium(self, benchmark):
        """Benchmark decoding medium objects (20 fields)."""
        obj = {f"field_{i}": i for i in range(20)}
        benchmark(decode_value, obj, "")

    def test_decode_object_nested(self, benchmark):
        """Benchmark decoding nested objects."""
        obj = {
            "user": {"name": "Bob", "email": "bob@example.com"},
            "scores": [85, 90, 78, 92],
            "metadata": {"created": "2024-01-15", "active": True},
        }
        benchmark(decode_value, obj, "")

    def test_decode_bytea_hex(self, benchmark):
        """Benchmark decoding bytea from hex."""
        hex_str = "\\x" + "0102030405" * 20  # 100 bytes
        benchmark(decode_value, hex_str, "BYTEA")

    def test_decode_uuid(self, benchmark):
        """Benchmark decoding UUID values."""
        benchmark(decode_value, "550e8400-e29b-41d4-a716-446655440000", "UUID")

    def test_decode_json_string(self, benchmark):
        """Benchmark decoding JSON type."""
        benchmark(decode_value, '{"key": "value", "num": 123}', "JSON")


# ============================================================================
# Value accessor benchmarks
# ============================================================================

class TestValueAccessorBenchmarks:
    """Benchmarks for Value type accessors."""

    def test_as_int(self, benchmark):
        """Benchmark as_int accessor."""
        val = Value(kind=ValueKind.INT, int_value=42)
        benchmark(lambda: val.as_int)

    def test_as_bool(self, benchmark):
        """Benchmark as_bool accessor."""
        val = Value(kind=ValueKind.BOOL, bool_value=True)
        benchmark(lambda: val.as_bool)

    def test_as_string(self, benchmark):
        """Benchmark as_string accessor."""
        val = Value(kind=ValueKind.STRING, str_value="hello world")
        benchmark(lambda: val.as_string)

    def test_as_decimal(self, benchmark):
        """Benchmark as_decimal accessor."""
        val = Value(kind=ValueKind.DECIMAL, decimal_value=Decimal("123.456"))
        benchmark(lambda: val.as_decimal)

    def test_as_array(self, benchmark):
        """Benchmark as_array accessor."""
        items = [Value(kind=ValueKind.INT, int_value=i) for i in range(10)]
        val = Value(kind=ValueKind.ARRAY, array_value=items)
        benchmark(lambda: val.as_array)

    def test_as_object(self, benchmark):
        """Benchmark as_object accessor."""
        fields = {f"key_{i}": Value(kind=ValueKind.INT, int_value=i) for i in range(10)}
        val = Value(kind=ValueKind.OBJECT, object_value=fields)
        benchmark(lambda: val.as_object)

    def test_is_null_true(self, benchmark):
        """Benchmark is_null check (true case)."""
        val = Value(kind=ValueKind.NULL)
        benchmark(lambda: val.is_null)

    def test_is_null_false(self, benchmark):
        """Benchmark is_null check (false case)."""
        val = Value(kind=ValueKind.INT, int_value=42)
        benchmark(lambda: val.is_null)

    def test_raw_value_int(self, benchmark):
        """Benchmark raw_value for int."""
        val = Value(kind=ValueKind.INT, int_value=42)
        benchmark(lambda: val.raw_value)

    def test_raw_value_array(self, benchmark):
        """Benchmark raw_value for array (recursive conversion)."""
        items = [Value(kind=ValueKind.INT, int_value=i) for i in range(10)]
        val = Value(kind=ValueKind.ARRAY, array_value=items)
        benchmark(lambda: val.raw_value)

    def test_raw_value_object(self, benchmark):
        """Benchmark raw_value for object (recursive conversion)."""
        fields = {f"k{i}": Value(kind=ValueKind.INT, int_value=i) for i in range(10)}
        val = Value(kind=ValueKind.OBJECT, object_value=fields)
        benchmark(lambda: val.raw_value)


# ============================================================================
# Value construction benchmarks
# ============================================================================

class TestValueConstructionBenchmarks:
    """Benchmarks for Value construction."""

    def test_construct_null(self, benchmark):
        """Benchmark NULL value construction."""
        benchmark(lambda: Value(kind=ValueKind.NULL))

    def test_construct_int(self, benchmark):
        """Benchmark INT value construction."""
        benchmark(lambda: Value(kind=ValueKind.INT, int_value=42))

    def test_construct_string(self, benchmark):
        """Benchmark STRING value construction."""
        benchmark(lambda: Value(kind=ValueKind.STRING, str_value="hello"))

    def test_construct_decimal(self, benchmark):
        """Benchmark DECIMAL value construction."""
        dec = Decimal("123.456")
        benchmark(lambda: Value(kind=ValueKind.DECIMAL, decimal_value=dec))

    def test_construct_array(self, benchmark):
        """Benchmark ARRAY value construction."""
        items = [Value(kind=ValueKind.INT, int_value=i) for i in range(5)]
        benchmark(lambda: Value(kind=ValueKind.ARRAY, array_value=items.copy()))

    def test_construct_object(self, benchmark):
        """Benchmark OBJECT value construction."""
        fields = {"a": Value(kind=ValueKind.INT, int_value=1)}
        benchmark(lambda: Value(kind=ValueKind.OBJECT, object_value=fields.copy()))


# ============================================================================
# Decimal parsing benchmarks
# ============================================================================

class TestDecimalParsingBenchmarks:
    """Benchmarks for Decimal parsing performance."""

    def test_parse_decimal_integer(self, benchmark):
        """Benchmark parsing integer as decimal."""
        benchmark(lambda: Decimal("123"))

    def test_parse_decimal_simple(self, benchmark):
        """Benchmark parsing simple decimal."""
        benchmark(lambda: Decimal("123.456"))

    def test_parse_decimal_high_precision(self, benchmark):
        """Benchmark parsing high-precision decimal."""
        benchmark(lambda: Decimal("123.456789012345678901234567890"))

    def test_parse_decimal_scientific(self, benchmark):
        """Benchmark parsing scientific notation."""
        benchmark(lambda: Decimal("1.23456E+10"))

    def test_parse_decimal_negative(self, benchmark):
        """Benchmark parsing negative decimal."""
        benchmark(lambda: Decimal("-999999999.999999999"))


# ============================================================================
# Timestamp parsing benchmarks
# ============================================================================

class TestTimestampParsingBenchmarks:
    """Benchmarks for timestamp parsing performance."""

    def test_parse_date_strptime(self, benchmark):
        """Benchmark date parsing with strptime."""
        benchmark(lambda: datetime.strptime("2024-01-15", "%Y-%m-%d").date())

    def test_parse_timestamp_fromisoformat(self, benchmark):
        """Benchmark timestamp parsing with fromisoformat."""
        benchmark(lambda: datetime.fromisoformat("2024-01-15T10:30:45"))

    def test_parse_timestamp_with_tz(self, benchmark):
        """Benchmark timestamp with timezone parsing."""
        benchmark(lambda: datetime.fromisoformat("2024-01-15T10:30:45+00:00"))

    def test_parse_timestamp_z_suffix(self, benchmark):
        """Benchmark timestamp with Z suffix (requires replacement)."""
        def parse():
            s = "2024-01-15T10:30:45Z"
            return datetime.fromisoformat(s.replace('Z', '+00:00'))
        benchmark(parse)


# ============================================================================
# Mixed workload benchmarks
# ============================================================================

class TestMixedWorkloadBenchmarks:
    """Benchmarks simulating realistic workloads."""

    def test_decode_typical_row(self, benchmark):
        """Benchmark decoding a typical query result row."""
        row = {
            "id": 12345,
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "age": 30,
            "active": True,
            "score": "85.5",
            "tags": ["developer", "python", "database"],
            "created_at": "2024-01-15T10:30:45",
        }

        def decode_row():
            result = {}
            for key, value in row.items():
                result[key] = decode_value(value, "")
            return result

        benchmark(decode_row)

    def test_decode_large_result_set(self, benchmark):
        """Benchmark decoding a large result set (100 rows)."""
        row_template = {
            "id": 0,
            "name": "User",
            "value": 100,
            "active": True,
        }
        rows = [{**row_template, "id": i, "name": f"User_{i}"} for i in range(100)]

        def decode_result_set():
            return [
                {k: decode_value(v, "") for k, v in row.items()}
                for row in rows
            ]

        benchmark(decode_result_set)

    def test_access_all_fields(self, benchmark):
        """Benchmark accessing all fields from a decoded row."""
        val = Value(
            kind=ValueKind.OBJECT,
            object_value={
                "id": Value(kind=ValueKind.INT, int_value=123),
                "name": Value(kind=ValueKind.STRING, str_value="Alice"),
                "active": Value(kind=ValueKind.BOOL, bool_value=True),
                "score": Value(kind=ValueKind.DECIMAL, decimal_value=Decimal("85.5")),
            }
        )

        def access_fields():
            obj = val.as_object
            return (
                obj["id"].as_int,
                obj["name"].as_string,
                obj["active"].as_bool,
                obj["score"].as_decimal,
            )

        benchmark(access_fields)

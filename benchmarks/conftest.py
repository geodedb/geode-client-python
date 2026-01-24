"""
Pytest configuration for benchmarks.

Uses pytest-benchmark for performance testing.
Run with: pytest benchmarks/ --benchmark-only
"""

import pytest


def pytest_configure(config):
    """Register benchmark markers."""
    config.addinivalue_line(
        "markers",
        "benchmark: mark test as a benchmark"
    )


# Common test data for benchmarks

SAMPLE_JSON_VALUES = {
    "null": None,
    "int_small": 42,
    "int_large": 9223372036854775807,
    "int_negative": -1000000,
    "bool_true": True,
    "bool_false": False,
    "string_short": "hello",
    "string_long": "x" * 1000,
    "string_unicode": "Hello, World! Привет мир!",
    "decimal": "123.456789012345",
    "array_small": [1, 2, 3, 4, 5],
    "array_large": list(range(100)),
    "object_small": {"name": "Alice", "age": 30},
    "object_nested": {
        "user": {"name": "Bob", "email": "bob@example.com"},
        "scores": [85, 90, 78, 92],
        "active": True,
    },
}

SAMPLE_DATE_STRINGS = [
    "2024-01-15",
    "2023-12-31",
    "2000-01-01",
    "1999-12-31",
]

SAMPLE_TIMESTAMP_STRINGS = [
    "2024-01-15T10:30:45",
    "2024-01-15T10:30:45Z",
    "2024-01-15T10:30:45+00:00",
    "2024-01-15T10:30:45.123456",
]

SAMPLE_DECIMAL_STRINGS = [
    "0",
    "123",
    "123.456",
    "123.456789012345678901234567890",
    "-999999999.999999999",
    "0.000000000000000001",
]


@pytest.fixture
def sample_json_values():
    """Provide sample JSON values for benchmarks."""
    return SAMPLE_JSON_VALUES


@pytest.fixture
def sample_dates():
    """Provide sample date strings for benchmarks."""
    return SAMPLE_DATE_STRINGS


@pytest.fixture
def sample_timestamps():
    """Provide sample timestamp strings for benchmarks."""
    return SAMPLE_TIMESTAMP_STRINGS


@pytest.fixture
def sample_decimals():
    """Provide sample decimal strings for benchmarks."""
    return SAMPLE_DECIMAL_STRINGS

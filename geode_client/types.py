"""
Type system for Geode values including DECIMAL, temporal types, and advanced types.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union


class ValueKind(Enum):
    """Kind of value stored in a Value object."""

    NULL = auto()
    INT = auto()
    BOOL = auto()
    STRING = auto()
    DECIMAL = auto()
    ARRAY = auto()
    OBJECT = auto()
    BYTEA = auto()
    DATE = auto()
    TIME = auto()
    TIMETZ = auto()
    TIMESTAMP = auto()
    TIMESTAMPTZ = auto()
    INTERVAL = auto()
    JSON = auto()
    JSONB = auto()
    XML = auto()
    URL = auto()
    DOMAIN = auto()
    UUID = auto()
    ENUM = auto()
    BIT_STRING = auto()
    RANGE = auto()
    NODE = auto()
    EDGE = auto()
    PATH = auto()


@dataclass
class Range:
    """Represents a range type value."""

    lower: Optional["Value"] = None
    upper: Optional["Value"] = None
    bounds: str = ""  # e.g., "[)" for [lower, upper)


@dataclass
class Value:
    """
    Native representation of Geode values.

    Supports all GQL types including DECIMAL, temporal types, and advanced types.
    """

    kind: ValueKind
    int_value: int = 0
    bool_value: bool = False
    str_value: str = ""
    decimal_value: Optional[Decimal] = None
    decimal_scale: str = ""
    array_value: Optional[List["Value"]] = None
    object_value: Optional[Dict[str, "Value"]] = None
    bytes_value: bytes = b""
    time_value: Optional[Union[datetime, date, time]] = None
    range_value: Optional[Range] = None

    # No __post_init__: avoid wasteful empty list/dict allocation for scalar types.
    # as_array and as_object already guard for None.

    @property
    def is_null(self) -> bool:
        """Check if value is NULL."""
        return self.kind == ValueKind.NULL

    @property
    def raw_value(self) -> Any:
        """Get the raw Python value for test compatibility."""
        if self.kind == ValueKind.NULL:
            return None
        elif self.kind == ValueKind.INT:
            return self.int_value
        elif self.kind == ValueKind.BOOL:
            return self.bool_value
        elif self.kind == ValueKind.STRING:
            return self.str_value
        elif self.kind == ValueKind.DECIMAL:
            return self.decimal_value
        elif self.kind == ValueKind.ARRAY:
            return [v.raw_value for v in self.array_value] if self.array_value else []
        elif self.kind == ValueKind.OBJECT:
            return (
                {k: v.raw_value for k, v in self.object_value.items()}
                if self.object_value
                else {}
            )
        elif self.kind == ValueKind.BYTEA:
            return self.bytes_value
        elif self.kind in (
            ValueKind.DATE,
            ValueKind.TIME,
            ValueKind.TIMESTAMP,
            ValueKind.TIMESTAMPTZ,
            ValueKind.TIMETZ,
        ):
            return self.time_value
        elif self.kind == ValueKind.RANGE:
            return self.range_value
        elif self.kind in (ValueKind.NODE, ValueKind.EDGE, ValueKind.PATH):
            return (
                {
                    k: v.raw_value if isinstance(v, Value) else v
                    for k, v in self.object_value.items()
                }
                if self.object_value
                else {}
            )
        else:
            # For other types, return str_value
            return self.str_value

    @property
    def as_int(self) -> int:
        """Get value as integer."""
        if self.kind == ValueKind.INT:
            return self.int_value
        raise ValueError(f"Cannot convert {self.kind} to int")

    @property
    def as_bool(self) -> bool:
        """Get value as boolean."""
        if self.kind == ValueKind.BOOL:
            return self.bool_value
        raise ValueError(f"Cannot convert {self.kind} to bool")

    @property
    def as_string(self) -> str:
        """Get value as string."""
        if self.kind == ValueKind.STRING:
            return self.str_value
        elif self.kind == ValueKind.INT:
            return str(self.int_value)
        elif self.kind == ValueKind.BOOL:
            return str(self.bool_value)
        elif self.kind == ValueKind.DECIMAL:
            return str(self.decimal_value)
        return self.str_value

    @property
    def as_decimal(self) -> Decimal:
        """Get value as Decimal."""
        if self.kind == ValueKind.DECIMAL and self.decimal_value is not None:
            return self.decimal_value
        raise ValueError(f"Cannot convert {self.kind} to Decimal")

    @property
    def as_array(self) -> List["Value"]:
        """Get value as array."""
        if self.kind == ValueKind.ARRAY and self.array_value is not None:
            return self.array_value
        raise ValueError(f"Cannot convert {self.kind} to array")

    @property
    def as_object(self) -> Dict[str, "Value"]:
        """Get value as object."""
        if self.kind == ValueKind.OBJECT and self.object_value is not None:
            return self.object_value
        raise ValueError(f"Cannot convert {self.kind} to object")

    @property
    def as_bytes(self) -> bytes:
        """Get value as bytes."""
        if self.kind == ValueKind.BYTEA:
            return self.bytes_value
        raise ValueError(f"Cannot convert {self.kind} to bytes")

    @property
    def as_datetime(self) -> datetime:
        """Get value as datetime."""
        if self.kind in (ValueKind.TIMESTAMP, ValueKind.TIMESTAMPTZ):
            if isinstance(self.time_value, datetime):
                return self.time_value
        raise ValueError(f"Cannot convert {self.kind} to datetime")

    @property
    def as_date(self) -> date:
        """Get value as date."""
        if self.kind == ValueKind.DATE:
            if isinstance(self.time_value, (date, datetime)):
                return (
                    self.time_value
                    if isinstance(self.time_value, date)
                    else self.time_value.date()
                )
        raise ValueError(f"Cannot convert {self.kind} to date")

    @property
    def as_range(self) -> Range:
        """Get value as range."""
        if self.kind == ValueKind.RANGE and self.range_value is not None:
            return self.range_value
        raise ValueError(f"Cannot convert {self.kind} to range")

    def __repr__(self) -> str:
        if self.kind == ValueKind.NULL:
            return "Value(NULL)"
        elif self.kind == ValueKind.INT:
            return f"Value(INT: {self.int_value})"
        elif self.kind == ValueKind.BOOL:
            return f"Value(BOOL: {self.bool_value})"
        elif self.kind == ValueKind.STRING:
            return f"Value(STRING: {self.str_value!r})"
        elif self.kind == ValueKind.DECIMAL:
            return f"Value(DECIMAL: {self.decimal_value})"
        elif self.kind == ValueKind.ARRAY:
            return f"Value(ARRAY: {len(self.array_value) if self.array_value else 0} items)"
        elif self.kind == ValueKind.OBJECT:
            return f"Value(OBJECT: {len(self.object_value) if self.object_value else 0} fields)"
        else:
            return f"Value({self.kind.name})"


def _decode_int(raw: Any) -> Value:
    try:
        return Value(kind=ValueKind.INT, int_value=int(raw))
    except (ValueError, TypeError):
        return Value(kind=ValueKind.STRING, str_value=str(raw))


def _decode_decimal(raw: Any) -> Value:
    s = str(raw).strip('"')
    try:
        dec = Decimal(s)
        scale = s.split(".")[-1] if "." in s else ""
        return Value(kind=ValueKind.DECIMAL, decimal_value=dec, decimal_scale=scale)
    except Exception:
        return Value(kind=ValueKind.DECIMAL, str_value=s)


def _decode_bool(raw: Any) -> Value:
    return Value(kind=ValueKind.BOOL, bool_value=bool(raw))


def _decode_bytea(raw: Any) -> Value:
    s = str(raw)
    if s.startswith("\\x"):
        return Value(
            kind=ValueKind.BYTEA, bytes_value=bytes.fromhex(s[2:]), str_value=s
        )
    return Value(kind=ValueKind.BYTEA, str_value=s)


def _decode_date(raw: Any) -> Value:
    s = str(raw)
    try:
        dt = datetime.strptime(s, "%Y-%m-%d").date()
        return Value(kind=ValueKind.DATE, str_value=s, time_value=dt)
    except ValueError:
        return Value(kind=ValueKind.DATE, str_value=s)


def _decode_timestamp(raw: Any, kind: ValueKind) -> Value:
    s = str(raw)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return Value(kind=kind, str_value=s, time_value=dt)
    except ValueError:
        return Value(kind=kind, str_value=s)


def _decode_range(raw: Any) -> Value:
    if isinstance(raw, dict):
        r = Range()
        if "bounds" in raw:
            r.bounds = raw["bounds"]
        if "lower" in raw:
            r.lower = decode_value(raw["lower"], "")
        if "upper" in raw:
            r.upper = decode_value(raw["upper"], "")
        return Value(kind=ValueKind.RANGE, range_value=r)
    return Value(kind=ValueKind.RANGE, str_value=str(raw))


def _str_value(kind: ValueKind) -> Any:
    """Return a decoder that wraps raw as str_value with the given kind."""
    return lambda raw: Value(kind=kind, str_value=str(raw))


# Dispatch table for O(1) type lookup in decode_value()
_DECODERS: Dict[str, Any] = {
    "INT": _decode_int,
    "DECIMAL": _decode_decimal,
    "BOOL": _decode_bool,
    "STRING": _str_value(ValueKind.STRING),
    "BYTEA": _decode_bytea,
    "JSON": _str_value(ValueKind.JSON),
    "JSONB": _str_value(ValueKind.JSONB),
    "XML": _str_value(ValueKind.XML),
    "URL": _str_value(ValueKind.URL),
    "URI": _str_value(ValueKind.URL),
    "DOMAIN": _str_value(ValueKind.DOMAIN),
    "UUID": _str_value(ValueKind.UUID),
    "ENUM": _str_value(ValueKind.ENUM),
    "BIT": _str_value(ValueKind.BIT_STRING),
    "VARBIT": _str_value(ValueKind.BIT_STRING),
    "DATE": _decode_date,
    "TIMESTAMP": lambda raw: _decode_timestamp(raw, ValueKind.TIMESTAMP),
    "TIMESTAMPTZ": lambda raw: _decode_timestamp(raw, ValueKind.TIMESTAMPTZ),
    "TIME": _str_value(ValueKind.TIME),
    "TIMETZ": _str_value(ValueKind.TIMETZ),
    "INTERVAL": _str_value(ValueKind.INTERVAL),
}


def decode_value(raw: Any, type_name: str) -> Value:
    """
    Decode a JSON value into a typed Value object.

    Args:
        raw: Raw JSON value
        type_name: Type name from schema

    Returns:
        Decoded Value object
    """
    if raw is None:
        return Value(kind=ValueKind.NULL)

    type_upper = type_name.upper()

    # O(1) dispatch for known types
    decoder = _DECODERS.get(type_upper)
    if decoder is not None:
        return decoder(raw)

    # RANGE requires substring match
    if "RANGE" in type_upper:
        return _decode_range(raw)

    # Fallback: infer from Python type
    if isinstance(raw, list):
        return Value(
            kind=ValueKind.ARRAY, array_value=[decode_value(item, "") for item in raw]
        )
    if isinstance(raw, dict):
        return Value(
            kind=ValueKind.OBJECT,
            object_value={k: decode_value(v, "") for k, v in raw.items()},
        )
    if isinstance(raw, str):
        return Value(kind=ValueKind.STRING, str_value=raw)
    # Check bool BEFORE int because Python's bool is a subclass of int
    if isinstance(raw, bool):
        return Value(kind=ValueKind.BOOL, bool_value=raw)
    if isinstance(raw, int):
        return Value(kind=ValueKind.INT, int_value=raw)
    if isinstance(raw, float):
        return Value(kind=ValueKind.DECIMAL, decimal_value=Decimal(str(raw)))

    return Value(kind=ValueKind.STRING, str_value=str(raw))

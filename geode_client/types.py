"""
Type system for Geode values including DECIMAL, temporal types, and advanced types.
"""

from dataclasses import dataclass
from datetime import datetime, date, time
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


@dataclass
class Range:
    """Represents a range type value."""
    lower: Optional['Value'] = None
    upper: Optional['Value'] = None
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
    array_value: List['Value'] = None
    object_value: Dict[str, 'Value'] = None
    bytes_value: bytes = b""
    time_value: Optional[Union[datetime, date, time]] = None
    range_value: Optional[Range] = None

    def __post_init__(self):
        if self.array_value is None:
            self.array_value = []
        if self.object_value is None:
            self.object_value = {}

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
            return [v.raw_value for v in self.array_value]
        elif self.kind == ValueKind.OBJECT:
            return {k: v.raw_value for k, v in self.object_value.items()}
        elif self.kind == ValueKind.BYTEA:
            return self.bytes_value
        elif self.kind in (ValueKind.DATE, ValueKind.TIME, ValueKind.TIMESTAMP, ValueKind.TIMESTAMPTZ, ValueKind.TIMETZ):
            return self.time_value
        elif self.kind == ValueKind.RANGE:
            return self.range_value
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
        if self.kind == ValueKind.DECIMAL:
            return self.decimal_value
        raise ValueError(f"Cannot convert {self.kind} to Decimal")

    @property
    def as_array(self) -> List['Value']:
        """Get value as array."""
        if self.kind == ValueKind.ARRAY:
            return self.array_value
        raise ValueError(f"Cannot convert {self.kind} to array")

    @property
    def as_object(self) -> Dict[str, 'Value']:
        """Get value as object."""
        if self.kind == ValueKind.OBJECT:
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
                return self.time_value if isinstance(self.time_value, date) else self.time_value.date()
        raise ValueError(f"Cannot convert {self.kind} to date")

    @property
    def as_range(self) -> Range:
        """Get value as range."""
        if self.kind == ValueKind.RANGE:
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
            return f"Value(ARRAY: {len(self.array_value)} items)"
        elif self.kind == ValueKind.OBJECT:
            return f"Value(OBJECT: {len(self.object_value)} fields)"
        else:
            return f"Value({self.kind.name})"


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

    if type_upper == "INT":
        return Value(kind=ValueKind.INT, int_value=int(raw))
    elif type_upper == "DECIMAL":
        s = str(raw).strip('"')
        dec = Decimal(s)
        scale = s.split('.')[-1] if '.' in s else ""
        return Value(kind=ValueKind.DECIMAL, decimal_value=dec, decimal_scale=scale)
    elif type_upper == "BOOL":
        return Value(kind=ValueKind.BOOL, bool_value=bool(raw))
    elif type_upper == "STRING":
        return Value(kind=ValueKind.STRING, str_value=str(raw))
    elif type_upper == "BYTEA":
        s = str(raw)
        if s.startswith("\\x"):
            bytes_val = bytes.fromhex(s[2:])
            return Value(kind=ValueKind.BYTEA, bytes_value=bytes_val, str_value=s)
        return Value(kind=ValueKind.BYTEA, str_value=s)
    elif type_upper == "JSON":
        return Value(kind=ValueKind.JSON, str_value=str(raw))
    elif type_upper == "JSONB":
        return Value(kind=ValueKind.JSONB, str_value=str(raw))
    elif type_upper == "XML":
        return Value(kind=ValueKind.XML, str_value=str(raw))
    elif type_upper in ("URL", "URI"):
        return Value(kind=ValueKind.URL, str_value=str(raw))
    elif type_upper == "DOMAIN":
        return Value(kind=ValueKind.DOMAIN, str_value=str(raw))
    elif type_upper == "UUID":
        return Value(kind=ValueKind.UUID, str_value=str(raw))
    elif type_upper == "ENUM":
        return Value(kind=ValueKind.ENUM, str_value=str(raw))
    elif type_upper in ("BIT", "VARBIT"):
        return Value(kind=ValueKind.BIT_STRING, str_value=str(raw))
    elif type_upper == "DATE":
        s = str(raw)
        try:
            dt = datetime.strptime(s, "%Y-%m-%d").date()
            return Value(kind=ValueKind.DATE, str_value=s, time_value=dt)
        except ValueError:
            return Value(kind=ValueKind.DATE, str_value=s)
    elif type_upper == "TIMESTAMP":
        s = str(raw)
        try:
            dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
            return Value(kind=ValueKind.TIMESTAMP, str_value=s, time_value=dt)
        except ValueError:
            return Value(kind=ValueKind.TIMESTAMP, str_value=s)
    elif type_upper == "TIMESTAMPTZ":
        s = str(raw)
        try:
            dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
            return Value(kind=ValueKind.TIMESTAMPTZ, str_value=s, time_value=dt)
        except ValueError:
            return Value(kind=ValueKind.TIMESTAMPTZ, str_value=s)
    elif type_upper == "TIME":
        return Value(kind=ValueKind.TIME, str_value=str(raw))
    elif type_upper == "TIMETZ":
        return Value(kind=ValueKind.TIMETZ, str_value=str(raw))
    elif type_upper == "INTERVAL":
        return Value(kind=ValueKind.INTERVAL, str_value=str(raw))
    elif "RANGE" in type_upper:
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

    # Handle arrays and objects
    if isinstance(raw, list):
        arr = [decode_value(item, "") for item in raw]
        return Value(kind=ValueKind.ARRAY, array_value=arr)
    elif isinstance(raw, dict):
        obj = {k: decode_value(v, "") for k, v in raw.items()}
        return Value(kind=ValueKind.OBJECT, object_value=obj)
    elif isinstance(raw, str):
        return Value(kind=ValueKind.STRING, str_value=raw)
    # IMPORTANT: Check bool BEFORE int because Python's bool is a subclass of int
    # isinstance(True, int) returns True, so we must handle bool first
    elif isinstance(raw, bool):
        return Value(kind=ValueKind.BOOL, bool_value=raw)
    elif isinstance(raw, (int, float)):
        if isinstance(raw, int):
            return Value(kind=ValueKind.INT, int_value=raw)
        else:
            dec = Decimal(str(raw))
            return Value(kind=ValueKind.DECIMAL, decimal_value=dec)

    return Value(kind=ValueKind.STRING, str_value=str(raw))

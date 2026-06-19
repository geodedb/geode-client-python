"""GQL quoting/escaping helpers (mirrors Go quote.go).

These produce values safe to inline into GQL admin statements. They are
distinct from ``validate.identifier`` which only validates.
"""

from .client import GeodeError


class InvalidIdentifierError(GeodeError):
    """Raised when an identifier contains forbidden characters."""


class InvalidStringError(GeodeError):
    """Raised when a string literal contains forbidden control characters."""


def quote_ident(name: str) -> str:
    """Validate ``name`` as a bare GQL identifier and return it unchanged.

    Valid identifiers contain letters, digits, underscore, and hyphen, and
    must not start with a hyphen. Digits are permitted anywhere, including
    first. Raises InvalidIdentifierError for empty or invalid input.
    """
    if not name:
        raise InvalidIdentifierError("geode: identifier contains forbidden characters")
    for i, ch in enumerate(name):
        if ch.isascii() and (ch.isalpha() or ch == "_"):
            continue
        if ch.isascii() and ch.isdigit():
            continue
        if ch == "-":
            if i == 0:
                raise InvalidIdentifierError(
                    "geode: identifier contains forbidden characters"
                )
            continue
        raise InvalidIdentifierError("geode: identifier contains forbidden characters")
    return name


def quote_string(s: str) -> str:
    """Wrap ``s`` in GQL single quotes with backslashes and quotes escaped.

    ASCII control characters (< 0x20 or == 0x7F) are rejected. Escape order:
    backslash first (``\\`` -> ``\\\\``), then single quotes (``'`` -> ``''``).
    """
    for ch in s:
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            raise InvalidStringError(
                "geode: string literal contains forbidden characters"
            )
    s = s.replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


def sanitize_graph_name(name: str) -> str:
    """Strip any character that is not alphanumeric, underscore, or hyphen.

    Unlike :func:`quote_ident`, this never raises; it removes forbidden
    characters so the result can be inlined into a USE GRAPH statement.
    """
    out = []
    for ch in name:
        if (ch.isascii() and ch.isalnum()) or ch in ("_", "-"):
            out.append(ch)
    return "".join(out)

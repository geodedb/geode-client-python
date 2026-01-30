"""
Input validation module for Geode client.

Provides functions to validate user input before sending to server.
This helps catch errors early and provides clear error messages.
"""

import re
import ipaddress


class ValidationError(ValueError):
    """Raised when input validation fails."""

    pass


# Maximum lengths
MAX_QUERY_LENGTH = 1_000_000  # 1MB
MAX_PARAM_NAME_LENGTH = 64
MAX_HOSTNAME_LENGTH = 253
MAX_PAGE_SIZE = 100_000
MIN_PAGE_SIZE = 1
MIN_PORT = 1
MAX_PORT = 65535


def query(text: str, *, max_length: int = MAX_QUERY_LENGTH) -> str:
    """
    Validate a GQL query string.

    Args:
        text: The query string to validate
        max_length: Maximum allowed length (default 1MB)

    Returns:
        The validated query string (stripped of leading/trailing whitespace)

    Raises:
        ValidationError: If the query is invalid
    """
    if not isinstance(text, str):
        raise ValidationError(f"Query must be a string, got {type(text).__name__}")

    if not text or not text.strip():
        raise ValidationError("Query cannot be empty")

    if len(text) > max_length:
        raise ValidationError(
            f"Query too long: {len(text)} bytes exceeds maximum of {max_length}"
        )

    # Check for null bytes which could cause issues
    if "\x00" in text:
        raise ValidationError("Query cannot contain null bytes")

    return text.strip()


def param_name(name: str, *, max_length: int = MAX_PARAM_NAME_LENGTH) -> str:
    """
    Validate a parameter name.

    Parameter names must:
    - Start with a letter or underscore
    - Contain only letters, digits, and underscores
    - Be no longer than max_length characters

    Args:
        name: The parameter name to validate
        max_length: Maximum allowed length (default 64)

    Returns:
        The validated parameter name

    Raises:
        ValidationError: If the parameter name is invalid
    """
    if not isinstance(name, str):
        raise ValidationError(
            f"Parameter name must be a string, got {type(name).__name__}"
        )

    if not name:
        raise ValidationError("Parameter name cannot be empty")

    if len(name) > max_length:
        raise ValidationError(
            f"Parameter name too long: {len(name)} exceeds maximum of {max_length}"
        )

    # Must start with letter or underscore, contain only alphanumeric and underscore
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValidationError(
            f"Invalid parameter name '{name}': must start with letter or underscore, "
            "and contain only letters, digits, and underscores"
        )

    return name


def hostname(host: str, *, allow_localhost: bool = True) -> str:
    """
    Validate a hostname, IPv4, or IPv6 address.

    Args:
        host: The hostname or IP address to validate
        allow_localhost: Whether to allow 'localhost' (default True)

    Returns:
        The validated hostname/IP

    Raises:
        ValidationError: If the hostname is invalid
    """
    if not isinstance(host, str):
        raise ValidationError(f"Hostname must be a string, got {type(host).__name__}")

    if not host:
        raise ValidationError("Hostname cannot be empty")

    host = host.strip()

    if len(host) > MAX_HOSTNAME_LENGTH:
        raise ValidationError(
            f"Hostname too long: {len(host)} exceeds maximum of {MAX_HOSTNAME_LENGTH}"
        )

    # Check for localhost
    if host.lower() == "localhost":
        if not allow_localhost:
            raise ValidationError("'localhost' is not allowed")
        return host.lower()

    # Try to parse as IPv4
    try:
        ipaddress.IPv4Address(host)
        return host
    except ipaddress.AddressValueError:
        pass

    # Try to parse as IPv6
    try:
        # Handle bracketed IPv6 addresses
        if host.startswith("[") and host.endswith("]"):
            ipaddress.IPv6Address(host[1:-1])
            return host
        ipaddress.IPv6Address(host)
        return f"[{host}]"  # Return bracketed form for URLs
    except ipaddress.AddressValueError:
        pass

    # Validate as hostname
    # Hostname labels must:
    # - Be 1-63 characters
    # - Start with alphanumeric
    # - End with alphanumeric
    # - Contain only alphanumeric and hyphens
    hostname_regex = re.compile(
        r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$"
    )

    if not hostname_regex.match(host):
        raise ValidationError(
            f"Invalid hostname '{host}': must be a valid hostname, IPv4, or IPv6 address"
        )

    return host.lower()


def port(value: int) -> int:
    """
    Validate a port number.

    Args:
        value: The port number to validate

    Returns:
        The validated port number

    Raises:
        ValidationError: If the port is invalid
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"Port must be an integer, got {type(value).__name__}")

    if value < MIN_PORT or value > MAX_PORT:
        raise ValidationError(
            f"Port must be between {MIN_PORT} and {MAX_PORT}, got {value}"
        )

    return value


def page_size(
    value: int,
    *,
    min_size: int = MIN_PAGE_SIZE,
    max_size: int = MAX_PAGE_SIZE,
) -> int:
    """
    Validate a page size for query results.

    Args:
        value: The page size to validate
        min_size: Minimum allowed size (default 1)
        max_size: Maximum allowed size (default 100,000)

    Returns:
        The validated page size

    Raises:
        ValidationError: If the page size is invalid
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(
            f"Page size must be an integer, got {type(value).__name__}"
        )

    if value < min_size:
        raise ValidationError(f"Page size must be at least {min_size}, got {value}")

    if value > max_size:
        raise ValidationError(f"Page size must be at most {max_size}, got {value}")

    return value


def dsn_url(url: str) -> str:
    """
    Validate a DSN/connection URL.

    Args:
        url: The URL to validate

    Returns:
        The validated URL

    Raises:
        ValidationError: If the URL is invalid
    """
    if not isinstance(url, str):
        raise ValidationError(f"URL must be a string, got {type(url).__name__}")

    if not url:
        raise ValidationError("URL cannot be empty")

    url = url.strip()

    # Check for basic URL structure
    # Accept: quic://, geode://, or just host:port
    if "://" in url:
        # Has scheme
        scheme_match = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*)://", url)
        if not scheme_match:
            raise ValidationError(f"Invalid URL scheme in '{url}'")

        scheme = scheme_match.group(1).lower()
        if scheme not in ("quic", "geode", "geodes", "https"):
            raise ValidationError(
                f"Unsupported URL scheme '{scheme}': expected 'quic' or 'geode'"
            )
    else:
        # No scheme - must be host:port or just host
        if not re.match(r"^[a-zA-Z0-9.\-\[\]:]+", url):
            raise ValidationError(f"Invalid URL format: '{url}'")

    return url


def identifier(name: str, *, max_length: int = 128) -> str:
    """
    Validate a GQL identifier (label, property name, etc).

    Args:
        name: The identifier to validate
        max_length: Maximum allowed length (default 128)

    Returns:
        The validated identifier

    Raises:
        ValidationError: If the identifier is invalid
    """
    if not isinstance(name, str):
        raise ValidationError(f"Identifier must be a string, got {type(name).__name__}")

    if not name:
        raise ValidationError("Identifier cannot be empty")

    if len(name) > max_length:
        raise ValidationError(
            f"Identifier too long: {len(name)} exceeds maximum of {max_length}"
        )

    # GQL identifiers: start with letter or underscore, contain alphanumeric and underscore
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValidationError(
            f"Invalid identifier '{name}': must start with letter or underscore, "
            "and contain only letters, digits, and underscores"
        )

    return name


def label(name: str, *, max_length: int = 128) -> str:
    """
    Validate a node/edge label.

    Labels follow the same rules as identifiers but typically start with uppercase.
    This function validates but does not enforce the uppercase convention.

    Args:
        name: The label to validate
        max_length: Maximum allowed length (default 128)

    Returns:
        The validated label

    Raises:
        ValidationError: If the label is invalid
    """
    return identifier(name, max_length=max_length)


def property_name(name: str, *, max_length: int = 128) -> str:
    """
    Validate a property name.

    Args:
        name: The property name to validate
        max_length: Maximum allowed length (default 128)

    Returns:
        The validated property name

    Raises:
        ValidationError: If the property name is invalid
    """
    return identifier(name, max_length=max_length)


def timeout(
    value: float, *, min_value: float = 0.0, max_value: float = 3600.0
) -> float:
    """
    Validate a timeout value in seconds.

    Args:
        value: The timeout value to validate
        min_value: Minimum allowed value (default 0.0)
        max_value: Maximum allowed value (default 3600.0 = 1 hour)

    Returns:
        The validated timeout value

    Raises:
        ValidationError: If the timeout is invalid
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValidationError(f"Timeout must be a number, got {type(value).__name__}")

    if value < min_value:
        raise ValidationError(f"Timeout must be at least {min_value}, got {value}")

    if value > max_value:
        raise ValidationError(f"Timeout must be at most {max_value}, got {value}")

    return float(value)


def email(address: str, *, max_length: int = 320) -> str:
    """
    Validate an email address format.

    This performs basic format validation. It does not verify the address exists.

    Args:
        address: The email address to validate
        max_length: Maximum allowed length (default 320, per RFC 5321)

    Returns:
        The validated email address (stripped and lowercased)

    Raises:
        ValidationError: If the email format is invalid
    """
    if not isinstance(address, str):
        raise ValidationError(f"Email must be a string, got {type(address).__name__}")

    if not address:
        raise ValidationError("Email cannot be empty")

    address = address.strip()

    if len(address) > max_length:
        raise ValidationError(
            f"Email too long: {len(address)} exceeds maximum of {max_length}"
        )

    # Basic RFC 5322 email format validation
    # Note: This is intentionally not overly strict to avoid rejecting valid addresses
    email_regex = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
        r"[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
        r"(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )

    if not email_regex.match(address):
        raise ValidationError(f"Invalid email format: '{address}'")

    return address.lower()


def pagination_limit(
    value: int,
    *,
    min_value: int = 1,
    max_value: int = 10000,
) -> int:
    """
    Validate a pagination limit.

    Args:
        value: The limit value to validate
        min_value: Minimum allowed value (default 1)
        max_value: Maximum allowed value (default 10000)

    Returns:
        The validated limit

    Raises:
        ValidationError: If the limit is invalid
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"Limit must be an integer, got {type(value).__name__}")

    if value < min_value:
        raise ValidationError(f"Limit must be at least {min_value}, got {value}")

    if value > max_value:
        raise ValidationError(f"Limit must be at most {max_value}, got {value}")

    return value


def pagination_offset(value: int, *, max_value: int = 1_000_000) -> int:
    """
    Validate a pagination offset.

    Args:
        value: The offset value to validate
        max_value: Maximum allowed value (default 1,000,000)

    Returns:
        The validated offset

    Raises:
        ValidationError: If the offset is invalid
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"Offset must be an integer, got {type(value).__name__}")

    if value < 0:
        raise ValidationError(f"Offset must be non-negative, got {value}")

    if value > max_value:
        raise ValidationError(f"Offset must be at most {max_value}, got {value}")

    return value


def pool_size(
    min_size: int,
    max_size: int,
    *,
    absolute_min: int = 0,
    absolute_max: int = 1000,
) -> tuple[int, int]:
    """
    Validate connection pool size parameters.

    Args:
        min_size: Minimum pool size
        max_size: Maximum pool size
        absolute_min: Absolute minimum allowed (default 0)
        absolute_max: Absolute maximum allowed (default 1000)

    Returns:
        Tuple of (validated_min_size, validated_max_size)

    Raises:
        ValidationError: If the pool sizes are invalid
    """
    if not isinstance(min_size, int) or isinstance(min_size, bool):
        raise ValidationError(
            f"min_size must be an integer, got {type(min_size).__name__}"
        )
    if not isinstance(max_size, int) or isinstance(max_size, bool):
        raise ValidationError(
            f"max_size must be an integer, got {type(max_size).__name__}"
        )

    if min_size < absolute_min:
        raise ValidationError(
            f"min_size must be at least {absolute_min}, got {min_size}"
        )

    if max_size > absolute_max:
        raise ValidationError(
            f"max_size must be at most {absolute_max}, got {max_size}"
        )

    if min_size > max_size:
        raise ValidationError(
            f"min_size ({min_size}) cannot be greater than max_size ({max_size})"
        )

    return min_size, max_size

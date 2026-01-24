"""
Unit tests for the validation module.
"""

import pytest
from geode_client import validate, ValidationError


class TestQueryValidation:
    """Tests for query validation."""

    def test_valid_simple_query(self):
        """Valid simple query should pass."""
        result = validate.query("RETURN 1")
        assert result == "RETURN 1"

    def test_valid_complex_query(self):
        """Valid complex query should pass."""
        result = validate.query(
            "MATCH (n:Person) WHERE n.age > 25 RETURN n.name ORDER BY n.name"
        )
        assert "MATCH" in result

    def test_query_strips_whitespace(self):
        """Query should strip leading/trailing whitespace."""
        result = validate.query("  RETURN 1  \n")
        assert result == "RETURN 1"

    def test_empty_query_raises(self):
        """Empty query should raise ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate.query("")

    def test_whitespace_only_query_raises(self):
        """Whitespace-only query should raise ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate.query("   \n\t   ")

    def test_none_query_raises(self):
        """None query should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate.query(None)  # type: ignore

    def test_non_string_query_raises(self):
        """Non-string query should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate.query(123)  # type: ignore

    def test_query_with_null_byte_raises(self):
        """Query with null byte should raise ValidationError."""
        with pytest.raises(ValidationError, match="null bytes"):
            validate.query("SELECT\x00* FROM users")

    def test_query_too_long_raises(self):
        """Query exceeding max length should raise ValidationError."""
        with pytest.raises(ValidationError, match="too long"):
            validate.query("x" * 100, max_length=50)

    def test_custom_max_length(self):
        """Custom max length should be respected."""
        result = validate.query("RETURN 1", max_length=100)
        assert result == "RETURN 1"


class TestParamNameValidation:
    """Tests for parameter name validation."""

    def test_valid_param_name(self):
        """Valid parameter name should pass."""
        assert validate.param_name("name") == "name"
        assert validate.param_name("user_id") == "user_id"
        assert validate.param_name("_private") == "_private"
        assert validate.param_name("Name123") == "Name123"

    def test_param_name_with_underscore_start(self):
        """Parameter name starting with underscore should pass."""
        result = validate.param_name("_param")
        assert result == "_param"

    def test_empty_param_name_raises(self):
        """Empty parameter name should raise ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate.param_name("")

    def test_none_param_name_raises(self):
        """None parameter name should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate.param_name(None)  # type: ignore

    def test_param_name_starting_with_digit_raises(self):
        """Parameter name starting with digit should raise ValidationError."""
        with pytest.raises(ValidationError, match="must start with letter"):
            validate.param_name("123abc")

    def test_param_name_with_special_chars_raises(self):
        """Parameter name with special characters should raise ValidationError."""
        with pytest.raises(ValidationError, match="must start with letter"):
            validate.param_name("my-param")
        with pytest.raises(ValidationError, match="must start with letter"):
            validate.param_name("my.param")
        with pytest.raises(ValidationError, match="must start with letter"):
            validate.param_name("my param")

    def test_param_name_too_long_raises(self):
        """Parameter name exceeding max length should raise ValidationError."""
        with pytest.raises(ValidationError, match="too long"):
            validate.param_name("a" * 100, max_length=64)


class TestHostnameValidation:
    """Tests for hostname validation."""

    def test_valid_hostname(self):
        """Valid hostname should pass."""
        assert validate.hostname("example.com") == "example.com"
        assert validate.hostname("sub.example.com") == "sub.example.com"
        assert validate.hostname("my-server") == "my-server"

    def test_localhost(self):
        """Localhost should pass by default."""
        assert validate.hostname("localhost") == "localhost"
        assert validate.hostname("LOCALHOST") == "localhost"

    def test_localhost_disallowed(self):
        """Localhost should fail when not allowed."""
        with pytest.raises(ValidationError, match="not allowed"):
            validate.hostname("localhost", allow_localhost=False)

    def test_valid_ipv4(self):
        """Valid IPv4 address should pass."""
        assert validate.hostname("192.168.1.1") == "192.168.1.1"
        assert validate.hostname("127.0.0.1") == "127.0.0.1"
        assert validate.hostname("0.0.0.0") == "0.0.0.0"

    def test_valid_ipv6(self):
        """Valid IPv6 address should pass."""
        assert validate.hostname("::1") == "[::1]"
        assert validate.hostname("[::1]") == "[::1]"
        assert validate.hostname("2001:db8::1") == "[2001:db8::1]"

    def test_empty_hostname_raises(self):
        """Empty hostname should raise ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate.hostname("")

    def test_none_hostname_raises(self):
        """None hostname should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate.hostname(None)  # type: ignore

    def test_invalid_hostname_raises(self):
        """Invalid hostname should raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid hostname"):
            validate.hostname("invalid..hostname")
        with pytest.raises(ValidationError, match="Invalid hostname"):
            validate.hostname("-invalid")

    def test_hostname_too_long_raises(self):
        """Hostname exceeding 253 characters should raise ValidationError."""
        long_hostname = "a" * 254
        with pytest.raises(ValidationError, match="too long"):
            validate.hostname(long_hostname)


class TestPortValidation:
    """Tests for port validation."""

    def test_valid_port(self):
        """Valid port numbers should pass."""
        assert validate.port(1) == 1
        assert validate.port(80) == 80
        assert validate.port(443) == 443
        assert validate.port(3141) == 3141
        assert validate.port(65535) == 65535

    def test_port_zero_raises(self):
        """Port 0 should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be between"):
            validate.port(0)

    def test_port_negative_raises(self):
        """Negative port should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be between"):
            validate.port(-1)

    def test_port_too_high_raises(self):
        """Port > 65535 should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be between"):
            validate.port(65536)

    def test_non_integer_port_raises(self):
        """Non-integer port should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate.port("80")  # type: ignore
        with pytest.raises(ValidationError, match="must be an integer"):
            validate.port(80.5)  # type: ignore

    def test_bool_port_raises(self):
        """Boolean port should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate.port(True)  # type: ignore


class TestPageSizeValidation:
    """Tests for page size validation."""

    def test_valid_page_size(self):
        """Valid page sizes should pass."""
        assert validate.page_size(1) == 1
        assert validate.page_size(100) == 100
        assert validate.page_size(1000) == 1000
        assert validate.page_size(100000) == 100000

    def test_page_size_zero_raises(self):
        """Page size 0 should raise ValidationError."""
        with pytest.raises(ValidationError, match="at least"):
            validate.page_size(0)

    def test_page_size_negative_raises(self):
        """Negative page size should raise ValidationError."""
        with pytest.raises(ValidationError, match="at least"):
            validate.page_size(-1)

    def test_page_size_too_high_raises(self):
        """Page size > 100000 should raise ValidationError."""
        with pytest.raises(ValidationError, match="at most"):
            validate.page_size(100001)

    def test_custom_min_max(self):
        """Custom min/max should be respected."""
        assert validate.page_size(50, min_size=10, max_size=100) == 50
        with pytest.raises(ValidationError, match="at least"):
            validate.page_size(5, min_size=10, max_size=100)
        with pytest.raises(ValidationError, match="at most"):
            validate.page_size(150, min_size=10, max_size=100)

    def test_non_integer_page_size_raises(self):
        """Non-integer page size should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate.page_size("100")  # type: ignore

    def test_bool_page_size_raises(self):
        """Boolean page size should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate.page_size(True)  # type: ignore


class TestDsnUrlValidation:
    """Tests for DSN URL validation."""

    def test_valid_quic_url(self):
        """Valid quic:// URL should pass."""
        result = validate.dsn_url("quic://localhost:3141")
        assert result == "quic://localhost:3141"

    def test_valid_geode_url(self):
        """Valid geode:// URL should pass."""
        result = validate.dsn_url("geode://example.com:3141")
        assert result == "geode://example.com:3141"

    def test_url_with_params(self):
        """URL with query parameters should pass."""
        result = validate.dsn_url("quic://localhost:3141?page_size=1000")
        assert "page_size=1000" in result

    def test_simple_host_port(self):
        """Simple host:port should pass."""
        result = validate.dsn_url("localhost:3141")
        assert result == "localhost:3141"

    def test_empty_url_raises(self):
        """Empty URL should raise ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate.dsn_url("")

    def test_none_url_raises(self):
        """None URL should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate.dsn_url(None)  # type: ignore

    def test_invalid_scheme_raises(self):
        """Invalid URL scheme should raise ValidationError."""
        with pytest.raises(ValidationError, match="Unsupported URL scheme"):
            validate.dsn_url("http://localhost:3141")
        with pytest.raises(ValidationError, match="Unsupported URL scheme"):
            validate.dsn_url("ftp://localhost:3141")


class TestIdentifierValidation:
    """Tests for identifier validation."""

    def test_valid_identifier(self):
        """Valid identifiers should pass."""
        assert validate.identifier("name") == "name"
        assert validate.identifier("Person") == "Person"
        assert validate.identifier("_id") == "_id"
        assert validate.identifier("node_123") == "node_123"

    def test_empty_identifier_raises(self):
        """Empty identifier should raise ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate.identifier("")

    def test_identifier_starting_with_digit_raises(self):
        """Identifier starting with digit should raise ValidationError."""
        with pytest.raises(ValidationError, match="must start with letter"):
            validate.identifier("123abc")

    def test_identifier_with_special_chars_raises(self):
        """Identifier with special characters should raise ValidationError."""
        with pytest.raises(ValidationError, match="must start with letter"):
            validate.identifier("my-identifier")

    def test_identifier_too_long_raises(self):
        """Identifier exceeding max length should raise ValidationError."""
        with pytest.raises(ValidationError, match="too long"):
            validate.identifier("a" * 200)


class TestLabelValidation:
    """Tests for label validation."""

    def test_valid_label(self):
        """Valid labels should pass."""
        assert validate.label("Person") == "Person"
        assert validate.label("EMPLOYEE") == "EMPLOYEE"
        assert validate.label("customer_order") == "customer_order"

    def test_label_follows_identifier_rules(self):
        """Labels should follow identifier validation rules."""
        with pytest.raises(ValidationError, match="must start with letter"):
            validate.label("123Label")


class TestPropertyNameValidation:
    """Tests for property name validation."""

    def test_valid_property_name(self):
        """Valid property names should pass."""
        assert validate.property_name("name") == "name"
        assert validate.property_name("created_at") == "created_at"
        assert validate.property_name("_internal") == "_internal"

    def test_property_name_follows_identifier_rules(self):
        """Property names should follow identifier validation rules."""
        with pytest.raises(ValidationError, match="must start with letter"):
            validate.property_name("123property")


class TestTimeoutValidation:
    """Tests for timeout validation."""

    def test_valid_timeout(self):
        """Valid timeout values should pass."""
        assert validate.timeout(0.0) == 0.0
        assert validate.timeout(30.0) == 30.0
        assert validate.timeout(3600.0) == 3600.0

    def test_integer_timeout(self):
        """Integer timeout should be converted to float."""
        assert validate.timeout(30) == 30.0

    def test_negative_timeout_raises(self):
        """Negative timeout should raise ValidationError."""
        with pytest.raises(ValidationError, match="at least"):
            validate.timeout(-1.0)

    def test_timeout_too_high_raises(self):
        """Timeout exceeding max should raise ValidationError."""
        with pytest.raises(ValidationError, match="at most"):
            validate.timeout(4000.0)

    def test_custom_min_max_timeout(self):
        """Custom min/max timeout should be respected."""
        assert validate.timeout(5.0, min_value=1.0, max_value=10.0) == 5.0
        with pytest.raises(ValidationError, match="at least"):
            validate.timeout(0.5, min_value=1.0, max_value=10.0)

    def test_non_numeric_timeout_raises(self):
        """Non-numeric timeout should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be a number"):
            validate.timeout("30")  # type: ignore


class TestPoolSizeValidation:
    """Tests for pool size validation."""

    def test_valid_pool_size(self):
        """Valid pool sizes should pass."""
        assert validate.pool_size(0, 10) == (0, 10)
        assert validate.pool_size(5, 50) == (5, 50)
        assert validate.pool_size(10, 10) == (10, 10)

    def test_min_greater_than_max_raises(self):
        """min_size > max_size should raise ValidationError."""
        with pytest.raises(ValidationError, match="cannot be greater than"):
            validate.pool_size(20, 10)

    def test_negative_min_size_raises(self):
        """Negative min_size should raise ValidationError."""
        with pytest.raises(ValidationError, match="at least"):
            validate.pool_size(-1, 10)

    def test_max_size_too_high_raises(self):
        """max_size exceeding absolute_max should raise ValidationError."""
        with pytest.raises(ValidationError, match="at most"):
            validate.pool_size(0, 1001)

    def test_custom_absolute_limits(self):
        """Custom absolute limits should be respected."""
        assert validate.pool_size(5, 50, absolute_min=5, absolute_max=50) == (5, 50)
        with pytest.raises(ValidationError, match="at least"):
            validate.pool_size(0, 50, absolute_min=5, absolute_max=50)

    def test_non_integer_pool_size_raises(self):
        """Non-integer pool sizes should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate.pool_size("5", 10)  # type: ignore
        with pytest.raises(ValidationError, match="must be an integer"):
            validate.pool_size(5, "10")  # type: ignore

    def test_bool_pool_size_raises(self):
        """Boolean pool sizes should raise ValidationError."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate.pool_size(True, 10)  # type: ignore


class TestValidationErrorInheritance:
    """Tests for ValidationError."""

    def test_validation_error_is_value_error(self):
        """ValidationError should be a subclass of ValueError."""
        assert issubclass(ValidationError, ValueError)

    def test_validation_error_message(self):
        """ValidationError should have proper message."""
        with pytest.raises(ValidationError) as exc_info:
            validate.query("")
        assert "cannot be empty" in str(exc_info.value)

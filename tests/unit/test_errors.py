"""Unit tests for the errors module: DriverError + classifiers."""

from geode_client import (
    DriverError,
    GeodeError,
    NoRowsError,
    is_auth_error,
    is_retryable_error,
    is_syntax_error,
)


class TestDriverError:
    def test_is_geode_error(self):
        assert issubclass(DriverError, GeodeError)

    def test_fields(self):
        e = DriverError(code="US001", status_class="42000", message="bad")
        assert e.code == "US001"
        assert e.status_class == "42000"
        assert e.message == "bad"

    def test_str_includes_code_and_message(self):
        e = DriverError(code="US001", status_class="42000", message="bad")
        assert "US001" in str(e)
        assert "bad" in str(e)

    def test_retryable_serialization(self):
        assert DriverError(code="x", status_class="40001").is_retryable()

    def test_retryable_deadlock(self):
        assert DriverError(code="x", status_class="40502").is_retryable()

    def test_not_retryable_syntax(self):
        assert not DriverError(code="x", status_class="42000").is_retryable()


class TestClassifiers:
    def test_is_auth_error_28000(self):
        assert is_auth_error(DriverError(code="x", status_class="28000"))

    def test_is_auth_error_08P01(self):
        assert is_auth_error(DriverError(code="x", status_class="08P01"))

    def test_is_auth_error_false(self):
        assert not is_auth_error(DriverError(code="x", status_class="42000"))

    def test_is_auth_error_none(self):
        assert is_auth_error(None) is False

    def test_is_auth_error_non_driver(self):
        assert is_auth_error(ValueError("x")) is False

    def test_is_syntax_error_true(self):
        assert is_syntax_error(DriverError(code="x", status_class="42000"))

    def test_is_syntax_error_false(self):
        assert not is_syntax_error(DriverError(code="x", status_class="28000"))

    def test_is_retryable_error_true(self):
        assert is_retryable_error(DriverError(code="x", status_class="40001"))

    def test_is_retryable_error_false(self):
        assert not is_retryable_error(DriverError(code="x", status_class="42000"))

    def test_is_retryable_error_non_driver(self):
        assert is_retryable_error(ValueError("x")) is False


class TestNoRowsError:
    def test_is_geode_error(self):
        assert issubclass(NoRowsError, GeodeError)

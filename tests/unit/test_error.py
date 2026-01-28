"""Unit tests for Geode error types."""

from geode_client import AuthError, GeodeConnectionError, GeodeError, QueryError


class TestGeodeError:
    """Tests for GeodeError base class."""

    def test_creation(self):
        """Test basic error creation."""
        err = GeodeError("Something went wrong")
        assert str(err) == "Something went wrong"

    def test_inheritance(self):
        """Test that GeodeError inherits from Exception."""
        err = GeodeError("test")
        assert isinstance(err, Exception)

    def test_empty_message(self):
        """Test error with empty message."""
        err = GeodeError("")
        assert str(err) == ""

    def test_with_args(self):
        """Test error with multiple args."""
        err = GeodeError("error", "additional", "info")
        assert err.args == ("error", "additional", "info")


class TestGeodeConnectionError:
    """Tests for GeodeConnectionError."""

    def test_creation(self):
        """Test connection error creation."""
        err = GeodeConnectionError("Connection refused")
        assert str(err) == "Connection refused"

    def test_inheritance_from_geode_error(self):
        """Test inheritance from GeodeError."""
        err = GeodeConnectionError("test")
        assert isinstance(err, GeodeError)
        assert isinstance(err, Exception)

    def test_catch_as_geode_error(self):
        """Test that GeodeConnectionError can be caught as GeodeError."""
        try:
            raise GeodeConnectionError("Connection failed")
        except GeodeError as e:
            assert str(e) == "Connection failed"

    def test_connection_refused_message(self):
        """Test typical connection refused message."""
        err = GeodeConnectionError(
            "Failed to establish QUIC connection: Connection refused"
        )
        assert "QUIC" in str(err)
        assert "Connection refused" in str(err)

    def test_timeout_message(self):
        """Test timeout error message."""
        err = GeodeConnectionError("Timeout waiting for HELLO response")
        assert "Timeout" in str(err)

    def test_tls_error_message(self):
        """Test TLS-related error message."""
        err = GeodeConnectionError(
            "TLS handshake failed: certificate verification failed"
        )
        assert "TLS" in str(err)


class TestQueryError:
    """Tests for QueryError."""

    def test_creation(self):
        """Test query error creation."""
        err = QueryError("Syntax error in query")
        assert str(err) == "Syntax error in query"

    def test_inheritance_from_geode_error(self):
        """Test inheritance from GeodeError."""
        err = QueryError("test")
        assert isinstance(err, GeodeError)
        assert isinstance(err, Exception)

    def test_catch_as_geode_error(self):
        """Test that QueryError can be caught as GeodeError."""
        try:
            raise QueryError("Invalid syntax")
        except GeodeError as e:
            assert str(e) == "Invalid syntax"

    def test_syntax_error_message(self):
        """Test syntax error message format."""
        err = QueryError("SYNTAX_ERROR: Unexpected token 'FROM'")
        assert "SYNTAX_ERROR" in str(err)

    def test_semantic_error_message(self):
        """Test semantic error message format."""
        err = QueryError("SEMANTIC_ERROR: Variable 'x' not defined")
        assert "SEMANTIC_ERROR" in str(err)

    def test_error_with_iso_code(self):
        """Test error message with ISO error code."""
        err = QueryError("22000: Data exception - invalid value")
        assert "22000" in str(err)


class TestAuthError:
    """Tests for AuthError."""

    def test_creation(self):
        """Test auth error creation."""
        err = AuthError("Invalid credentials")
        assert str(err) == "Invalid credentials"

    def test_inheritance_from_geode_error(self):
        """Test inheritance from GeodeError."""
        err = AuthError("test")
        assert isinstance(err, GeodeError)
        assert isinstance(err, Exception)

    def test_catch_as_geode_error(self):
        """Test that AuthError can be caught as GeodeError."""
        try:
            raise AuthError("Authentication failed")
        except GeodeError as e:
            assert str(e) == "Authentication failed"

    def test_invalid_password_message(self):
        """Test invalid password error message."""
        err = AuthError("Invalid password for user 'admin'")
        assert "Invalid password" in str(err)

    def test_user_not_found_message(self):
        """Test user not found error message."""
        err = AuthError("User 'unknown' not found")
        assert "not found" in str(err)

    def test_permission_denied_message(self):
        """Test permission denied error message."""
        err = AuthError("Permission denied: requires ADMIN role")
        assert "Permission denied" in str(err)


class TestErrorDistinction:
    """Tests for distinguishing between error types."""

    def test_distinct_types(self):
        """Test that error types are distinct."""
        geode_err = GeodeError("geode")
        conn_err = GeodeConnectionError("connection")
        query_err = QueryError("query")
        auth_err = AuthError("auth")

        # Each should be its own type
        assert type(geode_err) is GeodeError
        assert type(conn_err) is GeodeConnectionError
        assert type(query_err) is QueryError
        assert type(auth_err) is AuthError

    def test_selective_catch(self):
        """Test catching specific error types."""
        errors = [
            GeodeConnectionError("conn"),
            QueryError("query"),
            AuthError("auth"),
        ]

        for error in errors:
            # Should be catchable as its specific type
            try:
                raise error
            except type(error):
                pass  # Expected

    def test_catch_order_matters(self):
        """Test that catch order matters for exception hierarchy."""
        # More specific exceptions should be caught before general ones
        try:
            raise QueryError("specific error")
        except QueryError:
            caught_specific = True
        except GeodeError:
            caught_specific = False

        assert caught_specific


class TestErrorRaising:
    """Tests for raising and re-raising errors."""

    def test_raise_and_reraise(self):
        """Test raising and re-raising errors."""
        original = QueryError("original error")

        try:
            try:
                raise original
            except QueryError:
                raise  # Re-raise
        except QueryError as e:
            assert e is original

    def test_chained_exception(self):
        """Test exception chaining."""
        try:
            try:
                raise ValueError("root cause")
            except ValueError as e:
                raise GeodeConnectionError("wrapped error") from e
        except GeodeConnectionError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
            assert str(e.__cause__) == "root cause"

    def test_error_with_context(self):
        """Test error with implicit exception context."""
        try:
            try:
                raise ValueError("implicit cause")
            except ValueError:
                raise QueryError("secondary error")
        except QueryError as e:
            assert e.__context__ is not None
            assert isinstance(e.__context__, ValueError)

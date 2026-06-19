"""Geode error types and classifiers (mirrors Go errors.go).

DriverError carries an ISO/IEC 39075 status class used to classify
authentication, syntax, and retryable (serialization/deadlock) failures.
"""

from typing import Optional

from .client import GeodeError, QueryError

# ISO/IEC 39075 status class constants.
STATUS_SUCCESS = "00000"
STATUS_NO_DATA = "02000"
STATUS_TRANSACTION_STATE = "25000"
STATUS_AUTH = "28000"
STATUS_PASSWORD_RESET = "08P01"  # Geode-specific
STATUS_SERIALIZATION = "40001"
STATUS_DEADLOCK = "40502"
STATUS_SYNTAX = "42000"

_RETRYABLE_CLASSES = (STATUS_SERIALIZATION, STATUS_DEADLOCK)
_AUTH_CLASSES = (STATUS_AUTH, STATUS_PASSWORD_RESET)


class DriverError(QueryError):
    """An error returned by the Geode server with an ISO/IEC 39075 status."""

    def __init__(
        self,
        code: str = "",
        status_class: str = "",
        message: str = "",
    ) -> None:
        self.code = code
        self.status_class = status_class
        self.message = message
        if message:
            super().__init__(f"{code}: {message}" if code else message)
        else:
            super().__init__(code)

    def is_retryable(self) -> bool:
        """Whether the operation may be retried (serialization/deadlock)."""
        return self.status_class in _RETRYABLE_CLASSES


class NoRowsError(GeodeError):
    """Raised when a single-row accessor finds no rows (Go: sql.ErrNoRows)."""


def is_auth_error(exc: Optional[BaseException]) -> bool:
    """Whether ``exc`` is an authentication/authorization failure."""
    if not isinstance(exc, DriverError):
        return False
    return exc.status_class in _AUTH_CLASSES


def is_syntax_error(exc: Optional[BaseException]) -> bool:
    """Whether ``exc`` is a GQL parse/syntax error (status 42000)."""
    if not isinstance(exc, DriverError):
        return False
    return exc.status_class == STATUS_SYNTAX


def is_retryable_error(exc: Optional[BaseException]) -> bool:
    """Whether ``exc`` is a retryable Geode error."""
    if not isinstance(exc, DriverError):
        return False
    return exc.is_retryable()

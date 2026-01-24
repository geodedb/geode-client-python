"""
Geode Python Client Library

A Python client library for Geode graph database with full GQL support.
"""

from .client import (
    Client,
    Connection,
    Page,
    Column,
    Savepoint,
    PreparedStatement,
    QueryPlan,
    QueryProfile,
    PlanOperation,
    BatchResult,
    open_database,
    GeodeError,
    GeodeConnectionError,
    QueryError,
    AuthError,
)
from .types import (
    Value,
    ValueKind,
    Range,
)
from .query_builder import (
    QueryBuilder,
    PatternBuilder,
    PredicateBuilder,
    EdgeDirection,
)
from .auth import (
    AuthClient,
    User,
    Role,
    Permission,
    RLSPolicy,
    SessionInfo,
)
from .pool import ConnectionPool
from . import validate
from .validate import ValidationError

__version__ = "0.1.0"
__all__ = [
    # Client
    "Client",
    "Connection",
    "Page",
    "Column",
    "Savepoint",
    "PreparedStatement",
    "QueryPlan",
    "QueryProfile",
    "PlanOperation",
    "BatchResult",
    "open_database",
    # Exceptions
    "GeodeError",
    "GeodeConnectionError",
    "QueryError",
    "AuthError",
    # Types
    "Value",
    "ValueKind",
    "Range",
    # Query Builder
    "QueryBuilder",
    "PatternBuilder",
    "PredicateBuilder",
    "EdgeDirection",
    # Auth
    "AuthClient",
    "User",
    "Role",
    "Permission",
    "RLSPolicy",
    "SessionInfo",
    # Pool
    "ConnectionPool",
    # Validation
    "validate",
    "ValidationError",
]

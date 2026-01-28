"""
Geode Python Client Library

A Python client library for Geode graph database with full GQL support.
"""

from . import validate
from .auth import (
    AuthClient,
    Permission,
    RLSPolicy,
    Role,
    SessionInfo,
    User,
)
from .client import (
    AuthError,
    BatchResult,
    Client,
    Column,
    Connection,
    GeodeConnectionError,
    GeodeError,
    Page,
    PlanOperation,
    PreparedStatement,
    QueryError,
    QueryPlan,
    QueryProfile,
    Savepoint,
    open_database,
)
from .pool import ConnectionPool
from .query_builder import (
    EdgeDirection,
    PatternBuilder,
    PredicateBuilder,
    QueryBuilder,
)
from .types import (
    Range,
    Value,
    ValueKind,
)
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

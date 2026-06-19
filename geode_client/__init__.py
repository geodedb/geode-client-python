"""
Geode Python Client Library

A Python client library for Geode graph database with full GQL support.
Supports both QUIC and gRPC transports with protobuf wire protocol.

Example:
    # Using QUIC transport (default)
    from geode_client import Client

    client = Client(host="localhost", port=3141, skip_verify=True)
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 1 AS x")
        print(page.rows[0]["x"].as_int)

    # Using gRPC transport
    client = Client.from_url("grpc://localhost:50051?tls=0")
    async with client.connection() as conn:
        page, _ = await conn.query("RETURN 1 AS x")
"""

from . import retry, validate
from .auth import (
    AuthClient,
    Permission,
    RLSPolicy,
    Role,
    SessionInfo,
    User,
)
from .batch import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_MAX_WORKERS,
    Statement,
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
    SecurityWarning,
    open_database,
)
from .errors import (
    DriverError,
    NoRowsError,
    is_auth_error,
    is_retryable_error,
    is_syntax_error,
)
from .pool import ConnectionPool, create_pool
from .query_builder import (
    EdgeDirection,
    PatternBuilder,
    PredicateBuilder,
    QueryBuilder,
)
from .retry import RetryPolicy, default_retry_policy
from .schema import parse_schema_fs
from .transport import (
    GrpcTransport,
    QuicTransport,
    Transport,
    TransportConfig,
    TransportConnectionError,
    TransportError,
    TransportType,
    UnsupportedSchemeError,
    create_transport,
    parse_dsn,
)
from .types import (
    Range,
    Value,
    ValueKind,
)
from .validate import ValidationError

__all__ = [
    # Client and connection
    "Client",
    "Connection",
    "open_database",
    # Result types
    "Page",
    "Column",
    "Value",
    "ValueKind",
    "Range",
    # Batch / schema
    "Statement",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_MAX_WORKERS",
    "parse_schema_fs",
    # Query building
    "QueryBuilder",
    "PatternBuilder",
    "PredicateBuilder",
    "EdgeDirection",
    # Transactions
    "Savepoint",
    # Prepared statements
    "PreparedStatement",
    "BatchResult",
    # Query analysis
    "QueryPlan",
    "QueryProfile",
    "PlanOperation",
    # Connection pool
    "ConnectionPool",
    "create_pool",
    # Authentication
    "AuthClient",
    "User",
    "Role",
    "Permission",
    "SessionInfo",
    "RLSPolicy",
    # Transport
    "TransportType",
    "TransportConfig",
    "Transport",
    "QuicTransport",
    "GrpcTransport",
    "create_transport",
    "parse_dsn",
    # Validation
    "validate",
    "ValidationError",
    # Errors
    "GeodeError",
    "GeodeConnectionError",
    "QueryError",
    "AuthError",
    "TransportError",
    "TransportConnectionError",
    "UnsupportedSchemeError",
    "SecurityWarning",
    "DriverError",
    "NoRowsError",
    "is_auth_error",
    "is_syntax_error",
    "is_retryable_error",
    # Retry
    "RetryPolicy",
    "default_retry_policy",
    "retry",
]

__version__ = "0.3.19"

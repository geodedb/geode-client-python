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

from . import validate
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
    GEODE_AUTH_ALT,
    NO_DATA,
    STATUS_AUTH,
    STATUS_DEADLOCK,
    STATUS_DEADLOCK_DETECTED,
    STATUS_SERIALIZATION,
    STATUS_SYNTAX,
    AuthError,
    BatchResult,
    Client,
    Column,
    Connection,
    ErrNoRows,
    GeodeConnectionError,
    GeodeError,
    NoRowsError,
    Page,
    PlanOperation,
    PreparedStatement,
    QueryError,
    QueryPlan,
    QueryProfile,
    Savepoint,
    SecurityWarning,
    is_auth_error,
    is_retryable_error,
    is_syntax_error,
    open_database,
)
from .crypto import Cipher, CryptoError
from .pool import ConnectionPool, create_pool, create_pool_from_dsn
from .query_builder import (
    EdgeDirection,
    PatternBuilder,
    PredicateBuilder,
    QueryBuilder,
)
from .quote import (
    InvalidIdentifierError,
    InvalidStringError,
    quote_ident,
    quote_string,
    sanitize_graph_name,
)
from .retry import RetryPolicy, default_retry_policy, retry
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
    format_dsn,
    parse_dsn,
    redact_dsn,
)
from .types import (
    Edge,
    Node,
    Path,
    Range,
    Value,
    ValueKind,
    as_edge,
    as_node,
    as_path,
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
    # Graph value types
    "Node",
    "Edge",
    "Path",
    "as_node",
    "as_edge",
    "as_path",
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
    # Batch / pipeline execution
    "Statement",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_MAX_WORKERS",
    # Schema loading
    "parse_schema_fs",
    # Retry
    "RetryPolicy",
    "default_retry_policy",
    "retry",
    # Field-level encryption
    "Cipher",
    "CryptoError",
    # GQL quoting helpers
    "quote_ident",
    "quote_string",
    "sanitize_graph_name",
    "InvalidIdentifierError",
    "InvalidStringError",
    # Query analysis
    "QueryPlan",
    "QueryProfile",
    "PlanOperation",
    # Connection pool
    "ConnectionPool",
    "create_pool",
    "create_pool_from_dsn",
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
    "format_dsn",
    "redact_dsn",
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
    "NoRowsError",
    "ErrNoRows",
    # Error classification (SQLSTATE predicates + constants)
    "is_auth_error",
    "is_syntax_error",
    "is_retryable_error",
    "STATUS_AUTH",
    "STATUS_SYNTAX",
    "STATUS_SERIALIZATION",
    "STATUS_DEADLOCK",
    "STATUS_DEADLOCK_DETECTED",
    "GEODE_AUTH_ALT",
    "NO_DATA",
]

__version__ = "0.4.0"

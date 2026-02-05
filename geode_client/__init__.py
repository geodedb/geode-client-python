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

__version__ = "0.2.0"
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
    "TransportError",
    "TransportConnectionError",
    "UnsupportedSchemeError",
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
    # Transport
    "Transport",
    "TransportType",
    "TransportConfig",
    "QuicTransport",
    "GrpcTransport",
    "parse_dsn",
    "create_transport",
]

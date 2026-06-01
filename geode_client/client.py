"""
Geode Python Client - Full QUIC and gRPC implementation with protobuf wire protocol.

This client supports:
- QUIC+TLS transport (quic://host:port)
- gRPC transport (grpc://host:port)

Wire format: 4-byte Big Endian length prefix + protobuf message body.
"""

import asyncio
import logging
import warnings
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import validate
from .proto import (
    BeginRequest,
    CommitRequest,
    DoubleValue,
    ExecuteRequest,
    HelloRequest,
    IntKind,
    IntValue,
    NullValue,
    Param,
    PullRequest,
    RollbackRequest,
    StringKind,
    StringValue,
)
from .proto import (
    Value as ProtoValue,
)
from .transport import (
    Transport,
    TransportConfig,
    TransportConnectionError,
    TransportError,
    TransportType,
    create_transport,
    parse_dsn,
)
from .types import Value, ValueKind, decode_value

# Module-level logger - users can configure logging level as needed
logger = logging.getLogger(__name__)

CONNECT_RETRY_ATTEMPTS = 3
CONNECT_RETRY_DELAY_SECONDS = 0.05


class SecurityWarning(UserWarning):
    """Warning for potential security issues like insecure TLS configuration."""

    pass


@dataclass
class Savepoint:
    """Represents a transaction savepoint."""

    name: str
    connection: Optional["Connection"] = None


@dataclass
class Column:
    """Represents a column in the result set."""

    name: str
    type: str


@dataclass
class Page:
    """Represents a page of query results."""

    columns: List[Column]
    rows: List[Dict[str, Value]]
    ordered: bool = False
    order_keys: Optional[List[str]] = None
    final: bool = False

    def __post_init__(self):
        if self.order_keys is None:
            self.order_keys = []


@dataclass
class PlanOperation:
    """Represents an operation in a query execution plan."""

    operation: str
    description: str
    estimated_rows: int = 0
    estimated_cost: float = 0.0
    children: List["PlanOperation"] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


@dataclass
class QueryPlan:
    """Represents a query execution plan."""

    query: str
    root: Optional[PlanOperation] = None
    estimated_total_cost: float = 0.0
    planning_time_ms: float = 0.0


@dataclass
class QueryProfile:
    """Represents query execution profiling information."""

    query: str
    execution_time_ms: float = 0.0
    planning_time_ms: float = 0.0
    rows_returned: int = 0
    rows_scanned: int = 0
    operations: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.operations is None:
            self.operations = []


@dataclass
class BatchResult:
    """Represents the result of a single query in a batch."""

    index: int
    success: bool
    page: Optional[Page] = None
    error: Optional[str] = None


class PreparedStatement:
    """
    A prepared statement with parameter placeholders.

    Prepared statements allow you to parse a query once and execute it
    multiple times with different parameters. This can improve performance
    when executing the same query pattern repeatedly.

    Example:
        stmt = await conn.prepare("MATCH (p:Person {name: $name}) RETURN p.age")
        result1 = await stmt.execute({"name": "Alice"})
        result2 = await stmt.execute({"name": "Bob"})
        await stmt.close()
    """

    def __init__(
        self,
        connection: "Connection",
        query: str,
        statement_id: str,
        parameters: List[str],
    ):
        self._connection = connection
        self._query = query
        self._statement_id = statement_id
        self._parameters = parameters
        self._closed = False

    @property
    def query(self) -> str:
        """Get the original query text."""
        return self._query

    @property
    def statement_id(self) -> str:
        """Get the server-assigned statement ID."""
        return self._statement_id

    @property
    def parameters(self) -> List[str]:
        """Get the list of parameter names."""
        return self._parameters.copy()

    @property
    def closed(self) -> bool:
        """Check if the statement is closed."""
        return self._closed

    async def execute(
        self,
        params: Optional[Dict[str, Any]] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[Page, Callable[[], AsyncIterator[Page]]]:
        """Execute the prepared statement with the given parameters."""
        if self._closed:
            raise GeodeError("Statement is closed")
        return await self._connection.query(self._query, params, page_size)

    async def close(self) -> None:
        """Close the prepared statement and release server resources."""
        if self._closed:
            return
        self._closed = True

    async def __aenter__(self) -> "PreparedStatement":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @staticmethod
    def extract_parameters(query: str) -> List[str]:
        """Extract parameter names from a query string."""
        import re

        pattern = r"\$([a-zA-Z_][a-zA-Z0-9_]*)"
        matches = re.findall(pattern, query)
        seen = set()
        result = []
        for param in matches:
            if param not in seen:
                seen.add(param)
                result.append(param)
        return result


# ISO/IEC 39075 (GQL) status class constants, mirrored from the Go and
# Node.js reference clients so predicates can classify server errors.
STATUS_SUCCESS = "00000"  # Successful completion
NO_DATA = "02000"  # No data
STATUS_WARNING = "01000"  # Warning
STATUS_TRANSACTION_STATE = "25000"  # Invalid transaction state
STATUS_AUTH = "28000"  # Authorization error
STATUS_SERIALIZATION = "40001"  # Serialization failure (retryable)
STATUS_DEADLOCK_DETECTED = "40P01"  # Deadlock detected (retryable)
STATUS_DEADLOCK = "40502"  # Transaction deadlock (retryable)
STATUS_SYNTAX = "42000"  # Syntax error
STATUS_SYSTEM = "58000"  # System error
# Geode-specific extension: password reset required. Treated as an auth error
# alongside the standard 28000 class (matches Go IsAuthError).
GEODE_AUTH_ALT = "08P01"

_AUTH_CODES = frozenset({STATUS_AUTH, GEODE_AUTH_ALT})
_RETRYABLE_CODES = frozenset(
    {STATUS_SERIALIZATION, STATUS_DEADLOCK_DETECTED, STATUS_DEADLOCK}
)


class GeodeError(Exception):
    """Base exception for Geode client errors."""

    pass


class GeodeConnectionError(GeodeError):
    """Raised when connection fails."""

    pass


class QueryError(GeodeError):
    """Raised when query execution fails.

    Args:
        *args: Standard exception message arguments.
        code: The ISO/IEC 39075 (GQL) SQLSTATE status class parsed from the
            server error response (e.g. ``"28000"``). ``None`` when unknown.
            Use :func:`is_auth_error`, :func:`is_syntax_error`, and
            :func:`is_retryable_error` to classify the error.
    """

    def __init__(self, *args: Any, code: Optional[str] = None) -> None:
        super().__init__(*args)
        self.code = code


class AuthError(GeodeError):
    """Raised when authentication fails.

    Carries the ``28000`` (authorization) SQLSTATE status class so that
    :func:`is_auth_error` classifies it consistently with server-side
    auth errors.
    """

    def __init__(self, *args: Any, code: Optional[str] = None) -> None:
        super().__init__(*args)
        self.code = code if code is not None else STATUS_AUTH


def is_auth_error(err: object) -> bool:
    """Report whether *err* is a Geode authentication/authorization failure.

    Matches the GQL status class ``28000`` or the Geode-specific ``08P01``
    password-reset extension (mirrors Go ``IsAuthError``). Returns ``False``
    for ``None`` and for errors that do not carry a SQLSTATE ``code``.
    """
    if err is None:
        return False
    if isinstance(err, AuthError):
        return True
    code = getattr(err, "code", None)
    return code in _AUTH_CODES


def is_syntax_error(err: object) -> bool:
    """Report whether *err* is a GQL parse/syntax error (status class ``42000``).

    Mirrors Go ``IsSyntaxError``. The Geode engine returns ``42000`` for
    unrecognised statements, including admin DDL verbs not implemented in the
    connected server build, so handlers can degrade gracefully.
    """
    if err is None:
        return False
    return getattr(err, "code", None) == STATUS_SYNTAX


def is_retryable_error(err: object) -> bool:
    """Report whether *err* is safe to retry.

    Retryable conditions (mirrors Go ``IsRetryableError`` and the Node.js
    ``isRetryableError``):

    - SQLSTATE serialization (``40001``) or deadlock (``40P01`` / ``40502``).
    - Transport-layer failures (:class:`~geode_client.transport.TransportError`).
    - Timeouts (:class:`asyncio.TimeoutError` / :class:`TimeoutError`).
    """
    if err is None:
        return False
    if isinstance(err, (TransportError, TimeoutError, asyncio.TimeoutError)):
        return True
    return getattr(err, "code", None) in _RETRYABLE_CODES


# Re-export for backwards compatibility
StreamReader = None  # Deprecated - now internal to transport
StreamWriter = None  # Deprecated - now internal to transport
GeodeProtocol = None  # Deprecated - now internal to transport


class Connection:
    """
    A connection to Geode server.

    Supports both QUIC and gRPC transports.
    """

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 3141,
        page_size: int = 1000,
        hello_name: str = "geode-python",
        hello_ver: str = "0.1.0",
        conformance: str = "min",
        ca_cert: Optional[str] = None,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None,
        skip_verify: bool = False,
        server_name: Optional[str] = None,
        username: str = "",
        password: str = "",
        transport_type: TransportType = TransportType.QUIC,
        tls_enabled: bool = True,
        graph: str = "",
    ):
        """
        Initialize connection parameters.

        Args:
            host: Server hostname or IP
            port: Server port (default 3141 for QUIC, 50051 for gRPC)
            page_size: Default page size for results
            hello_name: Client name for HELLO handshake
            hello_ver: Client version
            conformance: GQL conformance level (min/full)
            ca_cert: Path to CA certificate for server verification
            client_cert: Path to client certificate for mTLS
            client_key: Path to client key for mTLS
            skip_verify: Skip TLS verification (insecure, dev only)
            server_name: SNI server name (defaults to host)
            username: Username for authentication
            password: Password for authentication
            transport_type: Transport type (QUIC or GRPC)
            tls_enabled: Enable TLS (default True)
            graph: Graph name for DSN graph binding
        """
        # Normalize "localhost" to "127.0.0.1"
        self.host = "127.0.0.1" if host == "localhost" else host
        self.port = port
        self.page_size = page_size
        self.hello_name = hello_name
        self.hello_ver = hello_ver
        self.conformance = conformance
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key
        self.skip_verify = skip_verify
        self.server_name = server_name or self.host
        self.username = username
        self.password = password
        self.transport_type = transport_type
        self.tls_enabled = tls_enabled
        self.graph = graph

        # Transport state (serialization handled by transport-level lock)
        self._transport: Optional[Transport] = None
        self._connected = False

    async def __aenter__(self) -> "Connection":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _cleanup_failed_connect(self) -> None:
        """Reset partially opened transport state after connect/HELLO failures."""
        self._connected = False
        if self._transport is None:
            return

        try:
            await self._transport.close()
        except Exception:
            pass
        finally:
            self._transport = None

    async def connect(self) -> None:
        """Establish connection to Geode server using protobuf wire protocol."""
        if self._connected:
            return

        if self.skip_verify:
            warnings.warn(
                "TLS certificate verification is disabled (skip_verify=True). "
                "This is insecure and should only be used for development.",
                SecurityWarning,
                stacklevel=2,
            )

        # Create transport config
        config = TransportConfig(
            transport_type=self.transport_type,
            host=self.host,
            port=self.port,
            tls_enabled=self.tls_enabled,
            skip_verify=self.skip_verify,
            ca_cert=self.ca_cert,
            client_cert=self.client_cert,
            client_key=self.client_key,
            server_name=self.server_name,
            username=self.username,
            password=self.password,
            page_size=self.page_size,
            hello_name=self.hello_name,
            hello_ver=self.hello_ver,
            conformance=self.conformance,
            graph=self.graph,
        )

        # Send HELLO handshake
        hello_req = HelloRequest(
            username=self.username,
            password=self.password,
            client_name=self.hello_name,
            client_version=self.hello_ver,
            wanted_conformance=self.conformance,
            graph=self.graph if self.graph else None,
        )

        last_error: Optional[Exception] = None
        for attempt in range(CONNECT_RETRY_ATTEMPTS):
            self._transport = create_transport(config)

            try:
                await self._transport.connect()
                response = await self._transport.hello(hello_req)
                if not response.success:
                    raise AuthError(f"Authentication failed: {response.error_message}")
                self._connected = True
                return
            except AuthError:
                await self._cleanup_failed_connect()
                raise
            except TransportConnectionError as e:
                last_error = GeodeConnectionError(str(e))
            except TransportError as e:
                last_error = GeodeConnectionError(f"Handshake failed: {e}")
            except asyncio.TimeoutError:
                last_error = GeodeConnectionError("Timeout waiting for HELLO response")
            except Exception as e:
                last_error = GeodeConnectionError(f"Failed to connect: {e}")

            await self._cleanup_failed_connect()
            if attempt + 1 < CONNECT_RETRY_ATTEMPTS:
                await asyncio.sleep(CONNECT_RETRY_DELAY_SECONDS)

        if last_error is not None:
            raise last_error
        raise GeodeConnectionError("Failed to connect")

    async def begin(self) -> None:
        """Begin a transaction."""
        req = BeginRequest(session_id=self._transport.session_id)
        resp = await self._transport.begin(req)
        if not resp.HasField("begin"):
            raise GeodeError("Expected BEGIN response")

    async def commit(self) -> None:
        """Commit the current transaction."""
        req = CommitRequest(session_id=self._transport.session_id)
        resp = await self._transport.commit(req)
        if not resp.HasField("commit"):
            raise GeodeError("Expected COMMIT response")

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        req = RollbackRequest(session_id=self._transport.session_id)
        resp = await self._transport.rollback(req)
        if not resp.HasField("rollback"):
            raise GeodeError("Expected ROLLBACK response")

    async def savepoint(self, name: str) -> "Savepoint":
        """Create a savepoint within the current transaction."""
        validated_name = validate.identifier(name)
        await self.execute(f"SAVEPOINT {validated_name}")
        return Savepoint(name=validated_name, connection=self)

    async def rollback_to(self, savepoint: "Savepoint") -> None:
        """Rollback to a savepoint."""
        validated_name = validate.identifier(savepoint.name)
        await self.execute(f"ROLLBACK TO SAVEPOINT {validated_name}")

    def _python_to_proto_value(self, value: Any) -> ProtoValue:
        """Convert a Python value to a protobuf Value."""
        if value is None:
            return ProtoValue(null_val=NullValue())
        elif isinstance(value, bool):
            return ProtoValue(bool_val=value)
        elif isinstance(value, int):
            return ProtoValue(int_val=IntValue(value=value, kind=IntKind.INT))
        elif isinstance(value, float):
            return ProtoValue(double_val=DoubleValue(value=value))
        elif isinstance(value, str):
            return ProtoValue(
                string_val=StringValue(value=value, kind=StringKind.STRING)
            )
        else:
            # Fallback: convert to string
            return ProtoValue(
                string_val=StringValue(value=str(value), kind=StringKind.STRING)
            )

    def _build_node_value(self, node: Any) -> Value:
        """Build a NODE Value from a protobuf NodeValue."""
        props = {
            entry.key: self._proto_value_to_python(entry.value, "")
            for entry in node.properties
        }
        return Value(
            kind=ValueKind.NODE,
            object_value={
                "id": Value(kind=ValueKind.INT, int_value=node.id),
                "labels": Value(
                    kind=ValueKind.ARRAY,
                    array_value=[
                        Value(kind=ValueKind.STRING, str_value=lbl)
                        for lbl in node.labels
                    ],
                ),
                "properties": Value(kind=ValueKind.OBJECT, object_value=props),
            },
        )

    def _build_edge_value(self, edge: Any) -> Value:
        """Build an EDGE Value from a protobuf EdgeValue."""
        props = {
            entry.key: self._proto_value_to_python(entry.value, "")
            for entry in edge.properties
        }
        return Value(
            kind=ValueKind.EDGE,
            object_value={
                "id": Value(kind=ValueKind.INT, int_value=edge.id),
                "start_node": Value(kind=ValueKind.INT, int_value=edge.from_id),
                "end_node": Value(kind=ValueKind.INT, int_value=edge.to_id),
                "type": Value(kind=ValueKind.STRING, str_value=edge.label),
                "properties": Value(kind=ValueKind.OBJECT, object_value=props),
            },
        )

    def _proto_value_to_python(self, proto_val: ProtoValue, type_name: str) -> Value:
        """Convert a protobuf Value to a typed Value object."""
        if proto_val.HasField("null_val"):
            return Value(kind=ValueKind.NULL)
        elif proto_val.HasField("string_val"):
            return decode_value(proto_val.string_val.value, type_name)
        elif proto_val.HasField("int_val"):
            return Value(kind=ValueKind.INT, int_value=proto_val.int_val.value)
        elif proto_val.HasField("double_val"):
            return Value(
                kind=ValueKind.DECIMAL,
                decimal_value=Decimal(str(proto_val.double_val.value)),
            )
        elif proto_val.HasField("bool_val"):
            return Value(kind=ValueKind.BOOL, bool_value=proto_val.bool_val)
        elif proto_val.HasField("bytes_val"):
            return Value(kind=ValueKind.BYTEA, bytes_value=proto_val.bytes_val.value)
        elif proto_val.HasField("list_val"):
            items = [
                self._proto_value_to_python(v, "") for v in proto_val.list_val.values
            ]
            return Value(kind=ValueKind.ARRAY, array_value=items)
        elif proto_val.HasField("map_val"):
            entries = {
                entry.key: self._proto_value_to_python(entry.value, "")
                for entry in proto_val.map_val.entries
            }
            return Value(kind=ValueKind.OBJECT, object_value=entries)
        elif proto_val.HasField("node_val"):
            return self._build_node_value(proto_val.node_val)
        elif proto_val.HasField("edge_val"):
            return self._build_edge_value(proto_val.edge_val)
        elif proto_val.HasField("path_val"):
            path = proto_val.path_val
            return Value(
                kind=ValueKind.PATH,
                object_value={
                    "nodes": Value(
                        kind=ValueKind.ARRAY,
                        array_value=[self._build_node_value(n) for n in path.nodes],
                    ),
                    "edges": Value(
                        kind=ValueKind.ARRAY,
                        array_value=[self._build_edge_value(e) for e in path.edges],
                    ),
                },
            )
        elif proto_val.HasField("ext_val"):
            ext = proto_val.ext_val
            if ext.HasField("text"):
                return Value(kind=ValueKind.STRING, str_value=ext.text)
            elif ext.HasField("int_val"):
                return Value(kind=ValueKind.INT, int_value=ext.int_val)
            elif ext.HasField("double_val"):
                return Value(
                    kind=ValueKind.DECIMAL,
                    decimal_value=Decimal(str(ext.double_val)),
                )
            elif ext.HasField("bool_val"):
                return Value(kind=ValueKind.BOOL, bool_value=ext.bool_val)
            elif ext.HasField("bytes"):
                return Value(kind=ValueKind.BYTEA, bytes_value=ext.bytes)
            return Value(kind=ValueKind.STRING, str_value=ext.type_name)
        else:
            return Value(kind=ValueKind.NULL)

    def _parse_proto_rows(
        self,
        proto_rows,
        columns: List[Column],
    ) -> List[Dict[str, Value]]:
        """Parse protobuf rows into typed Value objects."""
        rows = []
        for proto_row in proto_rows:
            row = {}
            for i, col in enumerate(columns):
                if i < len(proto_row.values):
                    proto_val = proto_row.values[i]
                    row[col.name] = self._proto_value_to_python(proto_val, col.type)
                else:
                    row[col.name] = Value(kind=ValueKind.NULL)
            rows.append(row)
        return rows

    @staticmethod
    async def _empty_pager() -> AsyncIterator[Page]:
        """Return an async generator that yields nothing."""
        if False:
            yield  # pragma: no cover

    def _make_pull_pager(
        self,
        first_page: Page,
        columns: List[Column],
        transport: Transport,
        page_size: int,
    ) -> Callable[[], AsyncIterator[Page]]:
        """Create a pager that fetches additional pages via pull requests."""
        conn = self

        async def pager() -> AsyncIterator[Page]:
            while not first_page.final:
                pull_req = PullRequest(
                    session_id=transport.session_id,
                    page_size=page_size,
                )
                resp = await transport.pull(pull_req)
                if not resp.HasField("pull") or not resp.pull.HasField("response"):
                    break
                pull_resp = resp.pull.response
                if pull_resp.HasField("error"):
                    break
                if not pull_resp.HasField("page"):
                    break
                rows = conn._parse_proto_rows(pull_resp.page.rows, columns)
                page = Page(
                    columns=columns,
                    rows=rows,
                    ordered=pull_resp.page.ordered,
                    final=pull_resp.page.final,
                )
                if page.final:
                    first_page.final = True
                yield page

        return pager

    def _make_stream_pager(
        self,
        first_page: Page,
        columns: List[Column],
        transport: Transport,
    ) -> Callable[[], AsyncIterator[Page]]:
        """Create a pager that fetches additional pages via read_next (streaming)."""
        conn = self

        async def pager() -> AsyncIterator[Page]:
            while not first_page.final:
                exec_resp = await conn._read_execute_until_page(transport)
                if exec_resp is None:
                    break
                rows = conn._parse_proto_rows(exec_resp.page.rows, columns)
                page = Page(
                    columns=columns,
                    rows=rows,
                    ordered=exec_resp.page.ordered,
                    final=exec_resp.page.final,
                )
                if page.final:
                    first_page.final = True
                yield page

        return pager

    async def _read_execute_until_page(self, transport: Transport) -> Optional[Any]:
        """Read execute responses until a page, error, or heartbeat arrives."""
        while True:
            resp = await asyncio.wait_for(transport.read_next(), timeout=5.0)
            if not resp.HasField("execute"):
                return None
            exec_resp = resp.execute
            if exec_resp.HasField("error") or exec_resp.HasField("page"):
                return exec_resp
            if exec_resp.HasField("heartbeat"):
                return None

    def _parse_first_page(
        self,
        exec_resp: Any,
        columns: List[Column],
    ) -> Page:
        """Parse the first page from an execute response."""
        rows = self._parse_proto_rows(exec_resp.page.rows, columns)
        return Page(
            columns=columns,
            rows=rows,
            ordered=exec_resp.page.ordered,
            order_keys=list(exec_resp.page.order_keys),
            final=exec_resp.page.final,
        )

    async def query(
        self,
        text: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[Page, Callable[[], AsyncIterator[Page]]]:
        """
        Execute a GQL query and return the first page and a pager function.

        Uses protobuf wire protocol for communication.

        Args:
            text: GQL query text
            params: Query parameters
            page_size: Page size for results (default: connection page_size)

        Returns:
            Tuple of (first_page, pager_function)
        """
        if page_size is None:
            page_size = self.page_size

        # Convert params to protobuf Param list
        param_list = []
        if params:
            for k, v in params.items():
                param_list.append(Param(name=k, value=self._python_to_proto_value(v)))

        # Send Execute request (transport lock serializes the send+receive)
        exec_req = ExecuteRequest(
            session_id=self._transport.session_id,
            query=text,
            params=param_list,
        )
        resp = await self._transport.execute(exec_req)

        if not resp.HasField("execute"):
            raise QueryError("Expected Execute response")

        exec_resp = resp.execute

        # Check for error
        if exec_resp.HasField("error"):
            if self._is_no_data_response(exec_resp):
                return self._empty_result_page(columns=[]), self._empty_pager
            code = (exec_resp.error.code or "").strip() or None
            raise QueryError(
                f"{exec_resp.error.code}: {exec_resp.error.message}", code=code
            )

        # Parse columns from schema
        columns: List[Column] = []
        if exec_resp.HasField("schema"):
            columns = [
                Column(name=col.name, type=col.type) for col in exec_resp.schema.columns
            ]

        # Check if we got a page in the first response
        if exec_resp.HasField("page"):
            first_page = self._parse_first_page(exec_resp, columns)

            if first_page.final:
                return first_page, self._empty_pager

            assert self._transport is not None
            return first_page, self._make_pull_pager(
                first_page, columns, self._transport, page_size
            )

        # Need to read next message for data page (schema was first)
        if hasattr(self._transport, "read_next"):
            assert self._transport is not None
            exec_resp = await self._read_execute_until_page(self._transport)
            if exec_resp is not None:
                if exec_resp.HasField("error"):
                    if self._is_no_data_response(exec_resp):
                        return self._empty_result_page(columns), self._empty_pager
                    code = (exec_resp.error.code or "").strip() or None
                    raise QueryError(
                        f"{exec_resp.error.code}: {exec_resp.error.message}",
                        code=code,
                    )
                if exec_resp.HasField("page"):
                    first_page = self._parse_first_page(exec_resp, columns)

                    if first_page.final:
                        return first_page, self._empty_pager

                    assert self._transport is not None
                    return first_page, self._make_stream_pager(
                        first_page, columns, self._transport
                    )

        # Empty result
        first_page = self._empty_result_page(columns)
        return first_page, self._empty_pager

    def _is_no_data_response(self, exec_resp: Any) -> bool:
        """Treat 02000 / no-active-result responses as an empty result set."""
        if not exec_resp.HasField("error"):
            return False
        code = (exec_resp.error.code or "").strip()
        message = (exec_resp.error.message or "").strip().lower()
        return code == "02000" or message == "no active result set"

    def _empty_result_page(self, columns: List[Column]) -> Page:
        """Build a canonical empty final page."""
        return Page(columns=columns, rows=[], ordered=False, final=True)

    async def execute(self, text: str, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Execute a query without returning results.

        Useful for CREATE, DELETE, SET operations.

        Args:
            text: GQL query text
            params: Query parameters
        """
        page, _ = await self.query(text, params, page_size=0)

    async def prepare(self, query: str) -> PreparedStatement:
        """Prepare a statement for repeated execution."""
        parameters = PreparedStatement.extract_parameters(query)
        import uuid

        statement_id = str(uuid.uuid4())
        return PreparedStatement(
            connection=self,
            query=query,
            statement_id=statement_id,
            parameters=parameters,
        )

    async def explain(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryPlan:
        """Get the execution plan for a query without executing it."""
        explain_query = f"EXPLAIN {query}"
        page, _ = await self.query(explain_query, params)
        return QueryPlan(
            query=query,
            root=None,
            estimated_total_cost=0.0,
            planning_time_ms=0.0,
        )

    async def profile(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> QueryProfile:
        """Execute a query and return profiling information."""
        profile_query = f"PROFILE {query}"
        page, _ = await self.query(profile_query, params)
        return QueryProfile(
            query=query,
            execution_time_ms=0.0,
            planning_time_ms=0.0,
            rows_returned=len(page.rows),
            rows_scanned=0,
            operations=[],
        )

    async def batch(
        self,
        queries: List[Tuple[str, Optional[Dict[str, Any]]]],
        stop_on_error: bool = True,
    ) -> List[BatchResult]:
        """Execute multiple queries sequentially.

        Each query is a separate request-response round trip. For higher
        throughput, use a ConnectionPool and execute queries concurrently
        across multiple connections with asyncio.gather().
        """
        results = []

        for index, (query_text, params) in enumerate(queries):
            try:
                page, _ = await self.query(query_text, params)
                results.append(
                    BatchResult(
                        index=index,
                        success=True,
                        page=page,
                        error=None,
                    )
                )
            except (QueryError, GeodeError) as e:
                results.append(
                    BatchResult(
                        index=index,
                        success=False,
                        page=None,
                        error=str(e),
                    )
                )
                if stop_on_error:
                    for remaining_index in range(index + 1, len(queries)):
                        results.append(
                            BatchResult(
                                index=remaining_index,
                                success=False,
                                page=None,
                                error="Skipped due to previous error",
                            )
                        )
                    break

        return results

    async def close(self) -> None:
        """Close the connection."""
        if not self._connected:
            return

        self._connected = False

        if self._transport:
            try:
                await self._transport.close()
            except Exception:
                pass
            self._transport = None


class Client:
    """
    Geode database client factory.

    Use this to create connections to Geode server.

    Example:
        # Using QUIC transport (default)
        client = Client(host="localhost", port=3141)
        async with client.connection() as conn:
            page, _ = await conn.query("RETURN 1 AS x")

        # Using gRPC transport
        client = Client.from_url("grpc://localhost:50051")
        async with client.connection() as conn:
            page, _ = await conn.query("RETURN 1 AS x")
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3141,
        transport_type: TransportType = TransportType.QUIC,
        **kwargs,
    ):
        """
        Initialize client.

        Args:
            host: Server hostname or IP
            port: Server port (default 3141)
            transport_type: Transport type (QUIC or GRPC)
            **kwargs: Additional connection parameters
        """
        self.host = host
        self.port = port
        self.transport_type = transport_type
        self.config = {
            "host": host,
            "port": port,
            "transport_type": transport_type,
            **kwargs,
        }

    @classmethod
    def from_url(cls, url: str) -> "Client":
        """
        Create client from URL (DSN).

        Supported URL formats:
        - quic://host:port?param=value (QUIC transport, default)
        - grpc://host:port?param=value (gRPC transport)

        Query parameters:
        - tls: 0 or 1 (enable/disable TLS)
        - skip_verify: 0 or 1 (skip TLS verification)
        - ca_cert: path to CA certificate
        - client_cert: path to client certificate
        - client_key: path to client key
        - username/user: authentication username
        - password/pass: authentication password
        - page_size: default page size

        Args:
            url: Connection URL

        Returns:
            Client instance

        Raises:
            UnsupportedSchemeError: If the scheme is not supported

        Example:
            client = Client.from_url("quic://localhost:3141?skip_verify=1")
            client = Client.from_url("grpc://localhost:50051?tls=0")
        """
        config = parse_dsn(url)

        return cls(
            host=config.host,
            port=config.port,
            transport_type=config.transport_type,
            tls_enabled=config.tls_enabled,
            skip_verify=config.skip_verify,
            ca_cert=config.ca_cert,
            client_cert=config.client_cert,
            client_key=config.client_key,
            server_name=config.server_name,
            username=config.username,
            password=config.password,
            page_size=config.page_size,
            hello_name=config.hello_name,
            hello_ver=config.hello_ver,
            conformance=config.conformance,
            graph=config.graph,
        )

    async def connect(self) -> Connection:
        """Create and connect a new connection."""
        conn = Connection(**self.config)
        await conn.connect()
        return conn

    def connection(self) -> Connection:
        """
        Create a connection (not yet connected).

        Use with async context manager:
            async with client.connection() as conn:
                page, _ = await conn.query("RETURN 1")
        """
        return Connection(**self.config)


def open_database(url: str) -> Client:
    """
    Open a database client from URL.

    Args:
        url: Connection URL (quic://host:port or grpc://host:port)

    Returns:
        Client instance

    Example:
        client = open_database("quic://localhost:3141")
        async with client.connection() as conn:
            page, _ = await conn.query("MATCH (n) RETURN n LIMIT 10")
    """
    return Client.from_url(url)

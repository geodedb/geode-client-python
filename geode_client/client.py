"""
Geode Python Client - Full QUIC implementation.

This client uses QUIC+TLS for all connections to Geode server.
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import (
    QuicEvent,
    StreamDataReceived,
    StreamReset,
    ConnectionTerminated,
    StopSendingReceived,
)

from .types import Value, decode_value


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
        """
        Initialize a prepared statement.

        Args:
            connection: The connection this statement belongs to
            query: The original query text
            statement_id: Server-assigned statement ID
            parameters: List of parameter names found in the query
        """
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
        """
        Execute the prepared statement with the given parameters.

        Args:
            params: Parameter values (keys must match parameter names)
            page_size: Page size for results

        Returns:
            Tuple of (first_page, pager_function)

        Raises:
            GeodeError: If the statement is closed
            QueryError: If execution fails
        """
        if self._closed:
            raise GeodeError("Statement is closed")

        # For now, just execute the query directly with parameters
        # A full implementation would use the server's prepared statement feature
        return await self._connection.query(self._query, params, page_size)

    async def close(self) -> None:
        """Close the prepared statement and release server resources."""
        if self._closed:
            return
        self._closed = True
        # In a full implementation, we would send a CLOSE_STATEMENT message
        # For now, this is a no-op since we're executing queries directly

    async def __aenter__(self) -> "PreparedStatement":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @staticmethod
    def extract_parameters(query: str) -> List[str]:
        """
        Extract parameter names from a query string.

        Parameters are identified by $ followed by an identifier.

        Args:
            query: The query text

        Returns:
            List of unique parameter names (without $)

        Example:
            >>> PreparedStatement.extract_parameters("MATCH (n {id: $id, name: $name}) RETURN n")
            ['id', 'name']
        """
        import re

        # Match $identifier patterns
        pattern = r"\$([a-zA-Z_][a-zA-Z0-9_]*)"
        matches = re.findall(pattern, query)
        # Return unique parameters preserving order
        seen = set()
        result = []
        for param in matches:
            if param not in seen:
                seen.add(param)
                result.append(param)
        return result


class GeodeError(Exception):
    """Base exception for Geode client errors."""

    pass


class GeodeConnectionError(GeodeError):
    """Raised when connection fails."""

    pass


class QueryError(GeodeError):
    """Raised when query execution fails."""

    pass


class AuthError(GeodeError):
    """Raised when authentication fails."""

    pass


class StreamReader:
    """Async stream reader that wraps a queue."""

    def __init__(self, queue: asyncio.Queue):
        self._queue = queue
        self._buffer = b""

    async def read(self, n: int = -1) -> bytes:
        """Read up to n bytes from the stream."""
        # If we have buffered data, return it first
        if self._buffer:
            if n < 0 or len(self._buffer) <= n:
                data = self._buffer
                self._buffer = b""
                return data
            else:
                data = self._buffer[:n]
                self._buffer = self._buffer[n:]
                return data

        # Read from queue
        chunk = await self._queue.get()
        if chunk is None:  # End of stream
            return b""

        if n < 0 or len(chunk) <= n:
            return chunk
        else:
            self._buffer = chunk[n:]
            return chunk[:n]


class StreamWriter:
    """Async stream writer that wraps the protocol's write method."""

    def __init__(self, protocol: "GeodeProtocol", stream_id: int):
        self._protocol = protocol
        self._stream_id = stream_id

    def write(self, data: bytes) -> None:
        """Write data to the stream."""
        self._protocol.write_to_stream(self._stream_id, data)

    async def drain(self) -> None:
        """Wait for the write buffer to drain (no-op for QUIC)."""
        await asyncio.sleep(0)  # Yield control to event loop

    def close(self) -> None:
        """Close the stream."""
        self._protocol.close_stream(self._stream_id)


class GeodeProtocol(QuicConnectionProtocol):
    """
    QUIC protocol handler for Geode.

    Manages bidirectional streams for query execution.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stream_readers: Dict[int, asyncio.Queue] = {}
        self._stream_futures: Dict[int, asyncio.Future] = {}

    def quic_event_received(self, event: QuicEvent) -> None:
        """Handle QUIC events."""
        # Handle stream-related events ourselves (don't call super for these)
        # because we use Queue instead of StreamReader
        if isinstance(event, StreamDataReceived):
            stream_id = event.stream_id
            print(
                f"[DEBUG-QUIC] StreamDataReceived: stream_id={stream_id}, data_len={len(event.data)}, end_stream={event.end_stream}",
                file=sys.stderr,
            )

            # Create queue if not exists
            if stream_id not in self._stream_readers:
                print(
                    f"[DEBUG-QUIC] Creating new queue for stream {stream_id}",
                    file=sys.stderr,
                )
                self._stream_readers[stream_id] = asyncio.Queue()

            # Put data in queue
            if event.data:
                print(
                    f"[DEBUG-QUIC] Putting {len(event.data)} bytes into queue for stream {stream_id}",
                    file=sys.stderr,
                )
                self._stream_readers[stream_id].put_nowait(event.data)

            # Mark end of stream
            if event.end_stream:
                print(
                    f"[DEBUG-QUIC] Marking end of stream {stream_id}", file=sys.stderr
                )
                self._stream_readers[stream_id].put_nowait(None)
        elif isinstance(event, StreamReset):
            # Handle stream reset - mark stream as ended
            stream_id = event.stream_id
            if stream_id in self._stream_readers:
                self._stream_readers[stream_id].put_nowait(None)
        elif isinstance(event, (ConnectionTerminated, StopSendingReceived)):
            # Handle connection/stream termination - close all our queues
            for queue in self._stream_readers.values():
                try:
                    queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass
            # Don't call super() for these events - they expect StreamReader with feed_eof()
        else:
            # For all other events (handshake, connection state, etc.), let parent handle
            super().quic_event_received(event)

    async def create_bidirectional_stream(self) -> Tuple[int, asyncio.Queue]:
        """
        Create a new bidirectional stream.

        Returns:
            Tuple of (stream_id, reader_queue)
        """
        stream_id = self._quic.get_next_available_stream_id(is_unidirectional=False)
        reader_queue = asyncio.Queue()
        self._stream_readers[stream_id] = reader_queue
        print(f"[DEBUG] Created stream ID: {stream_id}", file=sys.stderr)
        return stream_id, reader_queue

    async def create_stream(self) -> Tuple["StreamReader", "StreamWriter"]:
        """
        Create a bidirectional stream and return reader/writer objects.

        Returns:
            Tuple of (reader, writer) objects compatible with asyncio streams
        """
        stream_id, queue = await self.create_bidirectional_stream()
        reader = StreamReader(queue)
        writer = StreamWriter(self, stream_id)
        return reader, writer

    def write_to_stream(
        self, stream_id: int, data: bytes, end_stream: bool = False
    ) -> None:
        """Write data to a stream."""
        print(
            f"[DEBUG] Writing {len(data)} bytes to stream {stream_id}", file=sys.stderr
        )
        self._quic.send_stream_data(stream_id, data, end_stream)
        self.transmit()
        print(f"[DEBUG] Transmitted data on stream {stream_id}", file=sys.stderr)

    async def read_from_stream(self, stream_id: int) -> Optional[bytes]:
        """Read data from a stream."""
        if stream_id not in self._stream_readers:
            raise GeodeConnectionError(f"Stream {stream_id} not found")

        data = await self._stream_readers[stream_id].get()
        return data

    def close_stream(self, stream_id: int) -> None:
        """Close a stream."""
        if stream_id in self._stream_readers:
            del self._stream_readers[stream_id]


class Connection:
    """
    A single QUIC connection to Geode server.

    Provides async interface for executing queries, managing transactions,
    and authentication.
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
    ):
        """
        Initialize connection parameters.

        Args:
            host: Server hostname or IP
            port: Server port (default 3141)
            page_size: Default page size for results
            hello_name: Client name for HELLO handshake
            hello_ver: Client version
            conformance: GQL conformance level (min/full)
            ca_cert: Path to CA certificate for server verification
            client_cert: Path to client certificate for mTLS
            client_key: Path to client key for mTLS
            skip_verify: Skip TLS verification (insecure, dev only)
            server_name: SNI server name (defaults to host)
        """
        # Normalize "localhost" to "127.0.0.1" to match vendor/quic examples
        # This avoids IPv4/IPv6 resolution issues
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
        # Use the normalized host for server_name to avoid SNI mismatch
        self.server_name = server_name or self.host

        # Connection state
        self._protocol = None
        self._connection_context = None
        self._reader = None
        self._writer = None
        self._connected = False
        self._lock = asyncio.Lock()
        self._buffer = b""

    async def __aenter__(self) -> "Connection":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Establish QUIC connection to Geode server."""
        print(
            f"[DEBUG] connect() called, already connected: {self._connected}",
            file=sys.stderr,
        )
        if self._connected:
            return

        # Configure QUIC - using same pattern as vendor/quic/clients/python/test_client.py
        print("[DEBUG] Configuring QUIC...", file=sys.stderr)
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["geode/1"],
        )

        # Configure TLS
        if self.skip_verify:
            # Skip certificate verification (match vendor client pattern)
            print(
                "[DEBUG] Skipping TLS verification (skip_verify=True)", file=sys.stderr
            )
            configuration.verify_mode = 0  # Same as ssl.CERT_NONE
            # DON'T set server_name when skipping verification - this causes cert issues
        else:
            # Set server name for SNI only when verifying
            configuration.server_name = self.server_name
            print(f"[DEBUG] Server name for SNI: {self.server_name}", file=sys.stderr)

            # Try to load CA certificate
            ca_cert_path = self.ca_cert

            # If no custom CA specified, try the test harness CA
            if not ca_cert_path:
                test_harness_ca = os.path.join(
                    os.path.dirname(__file__), "../../test-harness/certs/ca.crt"
                )
                if os.path.exists(test_harness_ca):
                    ca_cert_path = test_harness_ca
                    print(
                        f"[DEBUG] Using test harness CA: {test_harness_ca}",
                        file=sys.stderr,
                    )

            if ca_cert_path and os.path.exists(ca_cert_path):
                print(
                    f"[DEBUG] Loading CA certificate: {ca_cert_path}", file=sys.stderr
                )
                configuration.load_verify_locations(ca_cert_path)
            else:
                print(
                    "[DEBUG] WARNING: No CA certificate found and skip_verify=False",
                    file=sys.stderr,
                )

        if self.client_cert and self.client_key:
            print("[DEBUG] Loading client certificate", file=sys.stderr)
            configuration.load_cert_chain(self.client_cert, self.client_key)

        # Connect using async with pattern (proper context manager usage)
        print(f"[DEBUG] Connecting to {self.host}:{self.port}...", file=sys.stderr)

        try:
            # Store the async context manager
            self._connection_cm = connect(
                self.host,
                self.port,
                configuration=configuration,
                create_protocol=GeodeProtocol,
            )

            # Enter the context - this completes the QUIC handshake
            print("[DEBUG] Entering QUIC connection context...", file=sys.stderr)
            self._protocol = await self._connection_cm.__aenter__()
            print("[DEBUG] QUIC handshake complete", file=sys.stderr)

        except Exception as e:
            print(
                f"[DEBUG] QUIC connection failed: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            import traceback

            traceback.print_exc()
            raise GeodeConnectionError(f"Failed to establish QUIC connection: {e}")

        # Create bidirectional stream
        try:
            print("[DEBUG] Creating bidirectional stream...", file=sys.stderr)
            self._reader, self._writer = await self._protocol.create_stream()
            print("[DEBUG] Created bidirectional stream", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] Stream creation failed: {e}", file=sys.stderr)
            raise GeodeConnectionError(f"Failed to create stream: {e}")

        # Send HELLO message
        hello = {
            "type": "HELLO",
            "client_name": self.hello_name,
            "client_ver": self.hello_ver,
            "wanted_conformance": self.conformance,
        }
        print(f"[DEBUG] Sending HELLO message: {hello}", file=sys.stderr)
        await self._write_json(hello)
        print("[DEBUG] HELLO sent, waiting for response...", file=sys.stderr)

        # Read HELLO response with timeout
        try:
            response = await asyncio.wait_for(self._read_json(), timeout=5.0)
            print(f"[DEBUG] Received HELLO response: {response}", file=sys.stderr)
            if not response:
                raise GeodeConnectionError("No HELLO response from server")
        except asyncio.TimeoutError:
            print("[DEBUG] HELLO response timed out!", file=sys.stderr)
            raise GeodeConnectionError("Timeout waiting for HELLO response")
        except Exception as e:
            print(f"[DEBUG] Error reading HELLO response: {e}", file=sys.stderr)
            raise GeodeConnectionError(f"Failed to read HELLO response: {e}")

        self._connected = True
        print("[DEBUG] Connection fully established", file=sys.stderr)

    async def _write_json(self, obj: Dict[str, Any]) -> None:
        """Write JSON object as a line."""
        if not self._writer:
            raise GeodeConnectionError("Not connected")

        line = json.dumps(obj) + "\n"
        self._writer.write(line.encode("utf-8"))
        await self._writer.drain()

    async def _read_line(self) -> bytes:
        """Read a single line from the stream."""
        if not self._reader:
            raise GeodeConnectionError("Not connected")

        while True:
            # Check if we have a complete line in buffer
            newline_idx = self._buffer.find(b"\n")
            if newline_idx != -1:
                line = self._buffer[:newline_idx]
                self._buffer = self._buffer[newline_idx + 1 :]
                return line

            # Read more data
            data = await self._reader.read(4096)
            if not data:
                # End of stream
                if self._buffer:
                    line = self._buffer
                    self._buffer = b""
                    return line
                raise GeodeConnectionError("Stream closed")

            self._buffer += data

    async def _read_json(self) -> Dict[str, Any]:
        """Read and parse JSON line."""
        line = await self._read_line()
        if not line:
            return {}
        return json.loads(line)

    async def begin(self) -> None:
        """Begin a transaction."""
        async with self._lock:
            await self._write_json({"type": "BEGIN"})
            await self._read_json()

    async def commit(self) -> None:
        """Commit the current transaction."""
        async with self._lock:
            await self._write_json({"type": "COMMIT"})
            await self._read_json()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        async with self._lock:
            await self._write_json({"type": "ROLLBACK"})
            await self._read_json()

    async def savepoint(self, name: str) -> "Savepoint":
        """
        Create a savepoint within the current transaction.

        Args:
            name: Savepoint name

        Returns:
            Savepoint object that can be used to rollback to this point

        Example:
            await conn.begin()
            await conn.execute("CREATE (p:Person {name: 'Alice'})")
            sp = await conn.savepoint("before_update")
            await conn.execute("SET p.age = 30")
            await conn.rollback_to(sp)  # Rolls back the SET operation
            await conn.commit()
        """
        async with self._lock:
            await self._write_json({"type": "SAVEPOINT", "name": name})
            await self._read_json()
        return Savepoint(name=name, connection=self)

    async def rollback_to(self, savepoint: "Savepoint") -> None:
        """
        Rollback to a savepoint.

        Args:
            savepoint: The savepoint to rollback to
        """
        async with self._lock:
            await self._write_json({"type": "ROLLBACK_TO", "name": savepoint.name})
            await self._read_json()

    async def query(
        self,
        text: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[Page, Callable[[], AsyncIterator[Page]]]:
        """
        Execute a GQL query and return the first page and a pager function.

        Args:
            text: GQL query text
            params: Query parameters
            page_size: Page size for results (default: connection page_size)

        Returns:
            Tuple of (first_page, pager_function)

        Example:
            page, pager = await conn.query("MATCH (n) RETURN n LIMIT 100")
            # Process first page
            for row in page.rows:
                print(row)
            # Get more pages
            async for next_page in pager():
                for row in next_page.rows:
                    print(row)
        """
        async with self._lock:
            if page_size is None:
                page_size = self.page_size

            # Send RUN_GQL message
            run_msg = {"type": "RUN_GQL", "text": text}
            if params:
                run_msg["params"] = params

            await self._write_json(run_msg)

            # Read schema frame
            schema_frame = await self._read_json()
            result = schema_frame.get("result", {})

            if result.get("type") == "ERROR":
                code = result.get("code", "UNKNOWN")
                message = result.get("message", "Query failed")
                raise QueryError(f"{code}: {message}")

            if result.get("type") != "SCHEMA":
                raise QueryError(f"Unexpected frame type: {result.get('type')}")

            # Parse columns
            columns = [
                Column(name=col["name"], type=col["type"])
                for col in result.get("columns", [])
            ]
            type_map = {col.name: col.type for col in columns}

            # Send PULL to get first page
            await self._write_json(
                {
                    "type": "PULL",
                    "request_id": 1,
                    "page_size": page_size,
                }
            )

            bindings_frame = await self._read_json()
            bindings_result = bindings_frame.get("result", {})

            if bindings_result.get("type") == "PROFILE":
                # Empty result set when profiling
                first_page = Page(
                    columns=columns,
                    rows=[],
                    ordered=False,
                    final=True,
                )

                async def empty_pager():
                    return
                    yield  # Make it a generator

                return first_page, empty_pager

            if bindings_result.get("type") == "RESULT":
                # Server sent complete result (no pagination needed)
                first_page = Page(
                    columns=columns,
                    rows=self._parse_rows(bindings_result.get("rows", []), type_map),
                    ordered=bindings_result.get("ordered", False),
                    order_keys=bindings_result.get("order_keys", []),
                    final=True,  # RESULT means all data is here
                )

                async def empty_pager():
                    if False:
                        yield  # Make it a generator but never yield

                return first_page, empty_pager

            if bindings_result.get("type") != "BINDINGS":
                raise QueryError(
                    f"Unexpected frame type: {bindings_result.get('type')}"
                )

            # Parse first page
            rows = self._parse_rows(bindings_result.get("rows", []), type_map)
            first_page = Page(
                columns=columns,
                rows=rows,
                ordered=bindings_result.get("ordered", False),
                order_keys=bindings_result.get("order_keys", []),
                final=bindings_result.get("final", False),
            )

            # If all results are in the first page, don't create a pager
            if first_page.final:

                async def empty_pager():
                    if False:
                        yield  # Make it a generator but never yield anything

                return first_page, empty_pager

            # Create pager function for multi-page results
            async def pager():
                nonlocal first_page
                while not first_page.final:
                    async with self._lock:
                        await self._write_json(
                            {
                                "type": "PULL",
                                "request_id": 1,
                                "page_size": page_size,
                            }
                        )
                        frame = await self._read_json()
                        result = frame.get("result", {})

                        if result.get("type") == "ERROR":
                            break

                        if result.get("type") != "BINDINGS":
                            break

                        rows = self._parse_rows(result.get("rows", []), type_map)
                        page = Page(
                            columns=columns,
                            rows=rows,
                            ordered=result.get("ordered", False),
                            order_keys=result.get("order_keys", []),
                            final=result.get("final", False),
                        )

                        if page.final:
                            first_page.final = True

                        yield page

            return first_page, pager

    def _parse_rows(
        self,
        raw_rows: List[Dict[str, Any]],
        type_map: Dict[str, str],
    ) -> List[Dict[str, Value]]:
        """Parse raw JSON rows into typed Value objects."""
        rows = []
        for raw_row in raw_rows:
            row = {}
            for col_name, raw_value in raw_row.items():
                col_type = type_map.get(col_name, "")
                row[col_name] = decode_value(raw_value, col_type)
            rows.append(row)
        return rows

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
        """
        Prepare a statement for repeated execution.

        Prepared statements parse the query once and can be executed
        multiple times with different parameters.

        Args:
            query: The GQL query text with parameter placeholders ($name)

        Returns:
            PreparedStatement that can be executed multiple times

        Example:
            stmt = await conn.prepare("MATCH (p:Person {name: $name}) RETURN p")
            async with stmt:
                page, _ = await stmt.execute({"name": "Alice"})
                page2, _ = await stmt.execute({"name": "Bob"})
        """
        # Extract parameters from query
        parameters = PreparedStatement.extract_parameters(query)

        # Generate a statement ID (in a full implementation, this would come from server)
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
        """
        Get the execution plan for a query without executing it.

        Args:
            query: The GQL query text
            params: Optional query parameters

        Returns:
            QueryPlan with estimated costs and operations

        Example:
            plan = await conn.explain("MATCH (n:Person) RETURN n")
            print(f"Estimated cost: {plan.estimated_total_cost}")
        """
        async with self._lock:
            # Send EXPLAIN message
            explain_msg = {"type": "EXPLAIN", "text": query}
            if params:
                explain_msg["params"] = params

            await self._write_json(explain_msg)

            # Read response
            response = await self._read_json()
            result = response.get("result", {})

            if result.get("type") == "ERROR":
                code = result.get("code", "UNKNOWN")
                message = result.get("message", "Explain failed")
                raise QueryError(f"{code}: {message}")

            # Parse the explain result
            plan_data = result.get("plan", {})

            def parse_operation(op_data: Dict[str, Any]) -> PlanOperation:
                children = [
                    parse_operation(child) for child in op_data.get("children", [])
                ]
                return PlanOperation(
                    operation=op_data.get("operation", "Unknown"),
                    description=op_data.get("description", ""),
                    estimated_rows=op_data.get("estimated_rows", 0),
                    estimated_cost=op_data.get("estimated_cost", 0.0),
                    children=children,
                )

            root = None
            if plan_data:
                root = parse_operation(plan_data)

            return QueryPlan(
                query=query,
                root=root,
                estimated_total_cost=result.get("estimated_total_cost", 0.0),
                planning_time_ms=result.get("planning_time_ms", 0.0),
            )

    async def profile(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> QueryProfile:
        """
        Execute a query and return profiling information.

        Unlike explain(), this actually executes the query and returns
        real execution statistics.

        Args:
            query: The GQL query text
            params: Optional query parameters

        Returns:
            QueryProfile with actual execution metrics

        Example:
            profile = await conn.profile("MATCH (n:Person) RETURN n")
            print(f"Execution time: {profile.execution_time_ms}ms")
            print(f"Rows scanned: {profile.rows_scanned}")
        """
        async with self._lock:
            # Send PROFILE message
            profile_msg = {"type": "PROFILE", "text": query}
            if params:
                profile_msg["params"] = params

            await self._write_json(profile_msg)

            # Read response
            response = await self._read_json()
            result = response.get("result", {})

            if result.get("type") == "ERROR":
                code = result.get("code", "UNKNOWN")
                message = result.get("message", "Profile failed")
                raise QueryError(f"{code}: {message}")

            return QueryProfile(
                query=query,
                execution_time_ms=result.get("execution_time_ms", 0.0),
                planning_time_ms=result.get("planning_time_ms", 0.0),
                rows_returned=result.get("rows_returned", 0),
                rows_scanned=result.get("rows_scanned", 0),
                operations=result.get("operations", []),
            )

    async def batch(
        self,
        queries: List[Tuple[str, Optional[Dict[str, Any]]]],
        stop_on_error: bool = True,
    ) -> List[BatchResult]:
        """
        Execute multiple queries in a single batch.

        This can be more efficient than executing queries one at a time
        when you have multiple independent operations.

        Args:
            queries: List of (query_text, params) tuples
            stop_on_error: If True, stop execution on first error

        Returns:
            List of BatchResult for each query

        Example:
            results = await conn.batch([
                ("CREATE (p:Person {name: $name})", {"name": "Alice"}),
                ("CREATE (p:Person {name: $name})", {"name": "Bob"}),
                ("MATCH (n:Person) RETURN count(n)", None),
            ])
            for result in results:
                if result.success:
                    print(f"Query {result.index}: success")
                else:
                    print(f"Query {result.index}: {result.error}")
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
                    # Add placeholder results for remaining queries
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

        # Close the stream writer if we have one
        if self._writer:
            try:
                self._writer.close()
            except Exception:
                pass
            self._writer = None

        self._reader = None

        # Exit the connection context manager
        if hasattr(self, "_connection_cm") and self._connection_cm and self._protocol:
            try:
                await self._connection_cm.__aexit__(None, None, None)
            except Exception:
                pass

        self._protocol = None
        self._connection_cm = None


class Client:
    """
    Geode database client factory.

    Use this to create connections to Geode server.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 3141, **kwargs):
        """
        Initialize client.

        Args:
            host: Server hostname or IP
            port: Server port (default 3141)
            **kwargs: Additional connection parameters
        """
        self.host = host
        self.port = port
        self.config = {"host": host, "port": port, **kwargs}

    @classmethod
    def from_url(cls, url: str) -> "Client":
        """
        Create client from URL.

        URL format: quic://host:port?param=value

        Args:
            url: Connection URL

        Returns:
            Client instance
        """
        parsed = urlparse(url)

        # Extract host and port
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 3141

        # Parse query parameters
        config = {}
        if parsed.query:
            params = parse_qs(parsed.query)

            if "page_size" in params:
                config["page_size"] = int(params["page_size"][0])
            if "hello_name" in params:
                config["hello_name"] = params["hello_name"][0]
            if "hello_ver" in params:
                config["hello_ver"] = params["hello_ver"][0]
            if "conformance" in params:
                config["conformance"] = params["conformance"][0]
            if "ca_cert" in params:
                config["ca_cert"] = params["ca_cert"][0]
            if "client_cert" in params:
                config["client_cert"] = params["client_cert"][0]
            if "client_key" in params:
                config["client_key"] = params["client_key"][0]
            if "skip_verify" in params:
                config["skip_verify"] = params["skip_verify"][0].lower() in (
                    "1",
                    "true",
                )
            if "server_name" in params:
                config["server_name"] = params["server_name"][0]

        return cls(host, port, **config)

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
        url: Connection URL (quic://host:port?options)

    Returns:
        Client instance

    Example:
        client = open_database("quic://localhost:3141")
        async with client.connection() as conn:
            page, _ = await conn.query("MATCH (n) RETURN n LIMIT 10")
    """
    return Client.from_url(url)

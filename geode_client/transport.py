"""
Transport layer abstraction for Geode client.

Supports:
- QUIC transport: quic://host:port (default)
- gRPC transport: grpc://host:port
"""

import abc
import asyncio
import os
import struct
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .proto import (
    BeginRequest,
    ClientPacket,
    CommitRequest,
    ExecuteRequest,
    HelloRequest,
    HelloResponse,
    PingRequest,
    PullRequest,
    QuicClientMessage,
    QuicServerMessage,
    RollbackRequest,
    ServerPacket,
)


class TransportType(Enum):
    """Supported transport types."""

    QUIC = "quic"
    GRPC = "grpc"


class TransportError(Exception):
    """Base exception for transport errors."""

    pass


class TransportConnectionError(TransportError):
    """Connection-related errors with transport + host/port info."""

    def __init__(self, message: str, transport: str, host: str, port: int):
        self.transport = transport
        self.host = host
        self.port = port
        super().__init__(f"{transport}://{host}:{port}: {message}")


class UnsupportedSchemeError(TransportError):
    """Raised when an unsupported DSN scheme is used."""

    def __init__(self, scheme: str):
        self.scheme = scheme
        super().__init__(
            f"Unsupported scheme: '{scheme}'. Supported schemes: quic://, grpc://"
        )


@dataclass
class TransportConfig:
    """Transport configuration parsed from DSN."""

    transport_type: TransportType
    host: str
    port: int
    tls_enabled: bool = True
    skip_verify: bool = False
    ca_cert: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None
    server_name: Optional[str] = None
    username: str = ""
    password: str = ""
    page_size: int = 1000
    hello_name: str = "geode-python"
    hello_ver: str = "0.1.0"
    conformance: str = "min"


def parse_dsn(dsn: str) -> TransportConfig:
    """
    Parse a DSN string into transport configuration.

    Supported formats:
    - quic://host:port?options
    - grpc://host:port?options
    - grcp://host:port?options (deprecated alias for grpc://)

    Query parameters:
    - tls: 0 or 1 (default: 1)
    - skip_verify: 0 or 1 (default: 0)
    - ca_cert: path to CA certificate
    - client_cert: path to client certificate
    - client_key: path to client key
    - server_name: SNI server name
    - username/user: authentication username
    - password/pass: authentication password
    - page_size: default page size (default: 1000)

    Args:
        dsn: Data source name string

    Returns:
        TransportConfig instance

    Raises:
        UnsupportedSchemeError: If the scheme is not quic://, grpc://, or grcp://
    """
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()

    # Handle grcp:// as deprecated alias for grpc://
    if scheme == "grcp":
        warnings.warn(
            "grcp:// scheme is deprecated, use grpc:// instead",
            DeprecationWarning,
            stacklevel=2,
        )
        scheme = "grpc"

    # Determine transport type
    if scheme == "quic" or scheme == "":
        transport_type = TransportType.QUIC
        default_port = 3141
    elif scheme == "grpc":
        transport_type = TransportType.GRPC
        default_port = 50051
    else:
        raise UnsupportedSchemeError(scheme)

    # Extract host - handle IPv6 addresses
    host = parsed.hostname or "127.0.0.1"
    if host == "localhost":
        host = "127.0.0.1"  # Normalize for IPv4/IPv6 compatibility

    port = parsed.port or default_port

    # Parse query parameters
    config = TransportConfig(
        transport_type=transport_type,
        host=host,
        port=port,
    )

    if parsed.query:
        params = parse_qs(parsed.query)

        # TLS settings
        if "tls" in params:
            config.tls_enabled = params["tls"][0].lower() in ("1", "true", "yes")
        if "skip_verify" in params:
            config.skip_verify = params["skip_verify"][0].lower() in (
                "1",
                "true",
                "yes",
            )
        if "ca_cert" in params:
            config.ca_cert = params["ca_cert"][0]
        if "client_cert" in params:
            config.client_cert = params["client_cert"][0]
        if "client_key" in params:
            config.client_key = params["client_key"][0]
        if "server_name" in params:
            config.server_name = params["server_name"][0]

        # Authentication
        if "username" in params:
            config.username = params["username"][0]
        elif "user" in params:
            config.username = params["user"][0]
        if "password" in params:
            config.password = params["password"][0]
        elif "pass" in params:
            config.password = params["pass"][0]

        # Protocol settings
        if "page_size" in params:
            config.page_size = int(params["page_size"][0])
        if "hello_name" in params:
            config.hello_name = params["hello_name"][0]
        if "hello_ver" in params:
            config.hello_ver = params["hello_ver"][0]
        if "conformance" in params:
            config.conformance = params["conformance"][0]

    return config


class Transport(abc.ABC):
    """Abstract base class for Geode transports."""

    @abc.abstractmethod
    async def connect(self) -> None:
        """Establish connection to the server."""
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        """Close the connection."""
        pass

    @abc.abstractmethod
    async def hello(self, request: HelloRequest) -> HelloResponse:
        """Send HELLO handshake."""
        pass

    @abc.abstractmethod
    async def execute(self, request: ExecuteRequest) -> QuicServerMessage:
        """Execute a query."""
        pass

    @abc.abstractmethod
    async def pull(self, request: PullRequest) -> QuicServerMessage:
        """Pull more results."""
        pass

    @abc.abstractmethod
    async def ping(self) -> bool:
        """Ping the server."""
        pass

    @abc.abstractmethod
    async def begin(self, request: BeginRequest) -> QuicServerMessage:
        """Begin a transaction."""
        pass

    @abc.abstractmethod
    async def commit(self, request: CommitRequest) -> QuicServerMessage:
        """Commit a transaction."""
        pass

    @abc.abstractmethod
    async def rollback(self, request: RollbackRequest) -> QuicServerMessage:
        """Rollback a transaction."""
        pass

    @property
    @abc.abstractmethod
    def session_id(self) -> str:
        """Get the current session ID."""
        pass


class QuicTransport(Transport):
    """QUIC transport using aioquic with protobuf wire format."""

    def __init__(self, config: TransportConfig):
        self.config = config
        self._protocol = None
        self._connection_cm = None
        self._reader = None
        self._writer = None
        self._buffer = b""
        self._lock = asyncio.Lock()
        self._session_id = ""
        self._connected = False

    @property
    def session_id(self) -> str:
        return self._session_id

    async def connect(self) -> None:
        """Establish QUIC connection."""
        if self._connected:
            return

        from aioquic.asyncio import connect
        from aioquic.asyncio.protocol import QuicConnectionProtocol
        from aioquic.quic.configuration import QuicConfiguration
        from aioquic.quic.events import (
            ConnectionTerminated,
            QuicEvent,
            StopSendingReceived,
            StreamDataReceived,
            StreamReset,
        )

        # Create protocol class with event handling
        class GeodeProtocol(QuicConnectionProtocol):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._stream_readers = {}

            def quic_event_received(self, event: QuicEvent) -> None:
                if isinstance(event, StreamDataReceived):
                    stream_id = event.stream_id
                    if stream_id not in self._stream_readers:
                        self._stream_readers[stream_id] = asyncio.Queue()
                    if event.data:
                        self._stream_readers[stream_id].put_nowait(event.data)
                    if event.end_stream:
                        self._stream_readers[stream_id].put_nowait(None)
                elif isinstance(event, StreamReset):
                    if event.stream_id in self._stream_readers:
                        self._stream_readers[event.stream_id].put_nowait(None)
                elif isinstance(event, (ConnectionTerminated, StopSendingReceived)):
                    for queue in self._stream_readers.values():
                        try:
                            queue.put_nowait(None)
                        except asyncio.QueueFull:
                            pass
                else:
                    super().quic_event_received(event)

            async def create_stream(self):
                stream_id = self._quic.get_next_available_stream_id(
                    is_unidirectional=False
                )
                queue = asyncio.Queue()
                self._stream_readers[stream_id] = queue
                return stream_id, queue

            def write_to_stream(
                self, stream_id: int, data: bytes, end_stream: bool = False
            ):
                self._quic.send_stream_data(stream_id, data, end_stream)
                self.transmit()

        # Configure QUIC
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["geode/1"],
        )

        if self.config.skip_verify:
            configuration.verify_mode = 0
        else:
            if self.config.server_name:
                configuration.server_name = self.config.server_name
            else:
                configuration.server_name = self.config.host

            if self.config.ca_cert and os.path.exists(self.config.ca_cert):
                configuration.load_verify_locations(self.config.ca_cert)

        if self.config.client_cert and self.config.client_key:
            configuration.load_cert_chain(
                self.config.client_cert, self.config.client_key
            )

        try:
            self._connection_cm = connect(
                self.config.host,
                self.config.port,
                configuration=configuration,
                create_protocol=GeodeProtocol,
            )
            self._protocol = await self._connection_cm.__aenter__()
        except Exception as e:
            raise TransportConnectionError(
                f"Failed to establish QUIC connection: {e}",
                "quic",
                self.config.host,
                self.config.port,
            )

        # Create bidirectional stream
        try:
            self._stream_id, self._reader_queue = await self._protocol.create_stream()
        except Exception as e:
            raise TransportConnectionError(
                f"Failed to create stream: {e}",
                "quic",
                self.config.host,
                self.config.port,
            )

        self._connected = True

    async def close(self) -> None:
        """Close QUIC connection."""
        if not self._connected:
            return

        self._connected = False

        if self._connection_cm and self._protocol:
            try:
                await self._connection_cm.__aexit__(None, None, None)
            except Exception:
                pass

        self._protocol = None
        self._connection_cm = None
        self._buffer = b""

    async def _write_message(self, msg: QuicClientMessage) -> None:
        """Write a length-prefixed protobuf message."""
        if not self._connected:
            raise TransportError("Not connected")

        # Wrap in ClientPacket
        packet = ClientPacket(quic=msg)
        data = packet.SerializeToString()

        # 4-byte big-endian length prefix
        frame = struct.pack(">I", len(data)) + data
        self._protocol.write_to_stream(self._stream_id, frame)

    async def _read_message(self) -> QuicServerMessage:
        """Read a length-prefixed protobuf message."""
        if not self._connected:
            raise TransportError("Not connected")

        # Read 4-byte length prefix
        while len(self._buffer) < 4:
            data = await self._reader_queue.get()
            if data is None:
                raise TransportError("Stream closed")
            self._buffer += data

        msg_len = struct.unpack(">I", self._buffer[:4])[0]
        total_needed = 4 + msg_len

        # Read message body
        while len(self._buffer) < total_needed:
            data = await self._reader_queue.get()
            if data is None:
                raise TransportError("Stream closed")
            self._buffer += data

        msg_data = self._buffer[4:total_needed]
        self._buffer = self._buffer[total_needed:]

        # Decode ServerPacket
        packet = ServerPacket()
        packet.ParseFromString(msg_data)

        if packet.HasField("quic"):
            return packet.quic
        else:
            raise TransportError("Invalid server response: missing quic field")

    def _try_read_from_buffer(self) -> Optional[QuicServerMessage]:
        """Try to read a message from buffer without blocking."""
        if len(self._buffer) < 4:
            return None

        msg_len = struct.unpack(">I", self._buffer[:4])[0]
        total_needed = 4 + msg_len

        if len(self._buffer) < total_needed:
            return None

        msg_data = self._buffer[4:total_needed]
        self._buffer = self._buffer[total_needed:]

        packet = ServerPacket()
        packet.ParseFromString(msg_data)

        if packet.HasField("quic"):
            return packet.quic
        return None

    async def hello(self, request: HelloRequest) -> HelloResponse:
        """Send HELLO handshake."""
        async with self._lock:
            msg = QuicClientMessage(hello=request)
            await self._write_message(msg)

            response = await asyncio.wait_for(self._read_message(), timeout=5.0)

            if response.HasField("hello"):
                if response.hello.success:
                    self._session_id = response.hello.session_id
                return response.hello
            else:
                raise TransportError("Expected HELLO response")

    async def execute(self, request: ExecuteRequest) -> QuicServerMessage:
        """Execute a query."""
        async with self._lock:
            msg = QuicClientMessage(execute=request)
            await self._write_message(msg)
            return await self._read_message()

    async def read_next(self) -> QuicServerMessage:
        """Read the next message (for streaming results)."""
        # First check buffer
        buffered = self._try_read_from_buffer()
        if buffered:
            return buffered
        return await self._read_message()

    async def pull(self, request: PullRequest) -> QuicServerMessage:
        """Pull more results."""
        async with self._lock:
            msg = QuicClientMessage(pull=request)
            await self._write_message(msg)
            return await self._read_message()

    async def ping(self) -> bool:
        """Ping the server."""
        async with self._lock:
            msg = QuicClientMessage(ping=PingRequest())
            await self._write_message(msg)
            response = await self._read_message()
            return response.HasField("ping") and response.ping.ok

    async def begin(self, request: BeginRequest) -> QuicServerMessage:
        """Begin a transaction."""
        async with self._lock:
            msg = QuicClientMessage(begin=request)
            await self._write_message(msg)
            return await self._read_message()

    async def commit(self, request: CommitRequest) -> QuicServerMessage:
        """Commit a transaction."""
        async with self._lock:
            msg = QuicClientMessage(commit=request)
            await self._write_message(msg)
            return await self._read_message()

    async def rollback(self, request: RollbackRequest) -> QuicServerMessage:
        """Rollback a transaction."""
        async with self._lock:
            msg = QuicClientMessage(rollback=request)
            await self._write_message(msg)
            return await self._read_message()


class GrpcTransport(Transport):
    """gRPC transport using grpcio."""

    def __init__(self, config: TransportConfig):
        self.config = config
        self._channel = None
        self._stub = None
        self._session_id = ""
        self._connected = False

    @property
    def session_id(self) -> str:
        return self._session_id

    async def connect(self) -> None:
        """Establish gRPC connection."""
        if self._connected:
            return

        import grpc

        from .proto import GeodeServiceStub

        target = f"{self.config.host}:{self.config.port}"

        if self.config.tls_enabled and not self.config.skip_verify:
            # Secure channel
            if self.config.ca_cert:
                with open(self.config.ca_cert, "rb") as f:
                    ca_cert = f.read()
            else:
                ca_cert = None

            if self.config.client_cert and self.config.client_key:
                with open(self.config.client_cert, "rb") as f:
                    client_cert = f.read()
                with open(self.config.client_key, "rb") as f:
                    client_key = f.read()
                credentials = grpc.ssl_channel_credentials(
                    root_certificates=ca_cert,
                    private_key=client_key,
                    certificate_chain=client_cert,
                )
            else:
                credentials = grpc.ssl_channel_credentials(root_certificates=ca_cert)

            self._channel = grpc.aio.secure_channel(target, credentials)
        else:
            # Insecure channel
            self._channel = grpc.aio.insecure_channel(target)

        self._stub = GeodeServiceStub(self._channel)
        self._connected = True

    async def close(self) -> None:
        """Close gRPC connection."""
        if not self._connected:
            return

        self._connected = False

        if self._channel:
            await self._channel.close()

        self._channel = None
        self._stub = None

    def _wrap_request(self, msg: QuicClientMessage) -> ClientPacket:
        """Wrap a QUIC message in a ClientPacket for gRPC."""
        return ClientPacket(quic=msg)

    def _unwrap_response(self, packet: ServerPacket) -> QuicServerMessage:
        """Unwrap a ServerPacket to get the QUIC message."""
        if packet.HasField("quic"):
            return packet.quic
        raise TransportError("Invalid server response: missing quic field")

    async def hello(self, request: HelloRequest) -> HelloResponse:
        """Send HELLO handshake via gRPC."""
        msg = QuicClientMessage(hello=request)
        packet = self._wrap_request(msg)

        try:
            response = await self._stub.Handshake(packet)
            quic_msg = self._unwrap_response(response)

            if quic_msg.HasField("hello"):
                if quic_msg.hello.success:
                    self._session_id = quic_msg.hello.session_id
                return quic_msg.hello
            else:
                raise TransportError("Expected HELLO response")
        except Exception as e:
            if "grpc" in type(e).__module__:
                raise TransportConnectionError(
                    str(e), "grpc", self.config.host, self.config.port
                )
            raise

    async def execute(self, request: ExecuteRequest) -> QuicServerMessage:
        """Execute a query via gRPC streaming."""
        msg = QuicClientMessage(execute=request)
        packet = self._wrap_request(msg)

        try:
            # Execute returns a stream - get first response
            stream = self._stub.Execute(packet)
            response = await stream.read()
            if response is None:
                raise TransportError("No response from server")
            return self._unwrap_response(response)
        except Exception as e:
            if "grpc" in type(e).__module__:
                raise TransportConnectionError(
                    str(e), "grpc", self.config.host, self.config.port
                )
            raise

    async def pull(self, request: PullRequest) -> QuicServerMessage:
        """Pull more results via gRPC."""
        msg = QuicClientMessage(pull=request)
        packet = self._wrap_request(msg)

        try:
            response = await self._stub.Pull(packet)
            return self._unwrap_response(response)
        except Exception as e:
            if "grpc" in type(e).__module__:
                raise TransportConnectionError(
                    str(e), "grpc", self.config.host, self.config.port
                )
            raise

    async def ping(self) -> bool:
        """Ping the server via gRPC."""
        msg = QuicClientMessage(ping=PingRequest())
        packet = self._wrap_request(msg)

        try:
            response = await self._stub.Ping(packet)
            quic_msg = self._unwrap_response(response)
            return quic_msg.HasField("ping") and quic_msg.ping.ok
        except Exception:
            return False

    async def begin(self, request: BeginRequest) -> QuicServerMessage:
        """Begin a transaction via gRPC."""
        msg = QuicClientMessage(begin=request)
        packet = self._wrap_request(msg)

        try:
            response = await self._stub.Begin(packet)
            return self._unwrap_response(response)
        except Exception as e:
            if "grpc" in type(e).__module__:
                raise TransportConnectionError(
                    str(e), "grpc", self.config.host, self.config.port
                )
            raise

    async def commit(self, request: CommitRequest) -> QuicServerMessage:
        """Commit a transaction via gRPC."""
        msg = QuicClientMessage(commit=request)
        packet = self._wrap_request(msg)

        try:
            response = await self._stub.Commit(packet)
            return self._unwrap_response(response)
        except Exception as e:
            if "grpc" in type(e).__module__:
                raise TransportConnectionError(
                    str(e), "grpc", self.config.host, self.config.port
                )
            raise

    async def rollback(self, request: RollbackRequest) -> QuicServerMessage:
        """Rollback a transaction via gRPC."""
        msg = QuicClientMessage(rollback=request)
        packet = self._wrap_request(msg)

        try:
            response = await self._stub.Rollback(packet)
            return self._unwrap_response(response)
        except Exception as e:
            if "grpc" in type(e).__module__:
                raise TransportConnectionError(
                    str(e), "grpc", self.config.host, self.config.port
                )
            raise


def create_transport(config: TransportConfig) -> Transport:
    """
    Create a transport instance based on configuration.

    Args:
        config: Transport configuration

    Returns:
        Transport instance (QuicTransport or GrpcTransport)
    """
    if config.transport_type == TransportType.QUIC:
        return QuicTransport(config)
    elif config.transport_type == TransportType.GRPC:
        return GrpcTransport(config)
    else:
        raise ValueError(f"Unknown transport type: {config.transport_type}")

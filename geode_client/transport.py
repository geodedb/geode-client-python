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
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .proto import (
    BeginRequest,
    CommitRequest,
    ExecuteRequest,
    HelloRequest,
    HelloResponse,
    PingRequest,
    PullRequest,
    QuicClientMessage,
    QuicServerMessage,
    RollbackRequest,
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

    See geode/docs/DSN.md for the full specification.

    Supported formats:
    - quic://host:port?options (recommended)
    - grpc://host:port?options
    - host:port?options (defaults to QUIC)

    Query parameters:
    - tls: 0/1/true/false (default: true, gRPC only)
    - insecure/skip_verify/insecure_skip_verify: skip TLS verification (default: false)
    - ca/ca_cert: path to CA certificate
    - cert/client_cert: path to client certificate
    - key/client_key: path to client key
    - server_name: SNI server name
    - username/user: authentication username
    - password/pass: authentication password
    - page_size: default page size (default: 1000)
    - hello_name: client name for HELLO
    - hello_ver: client version for HELLO
    - conformance: GQL conformance level
    - connect_timeout/timeout: connection timeout in seconds

    Args:
        dsn: Data source name string

    Returns:
        TransportConfig instance

    Raises:
        UnsupportedSchemeError: If the scheme is not supported
    """
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()

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

        # TLS settings (support multiple aliases per DSN spec)
        if "tls" in params:
            config.tls_enabled = params["tls"][0].lower() in ("1", "true", "yes", "on")

        # Insecure TLS skip verify aliases (primary: insecure_tls_skip_verify)
        for key in ("insecure_tls_skip_verify", "insecure", "skip_verify"):
            if key in params:
                config.skip_verify = params[key][0].lower() in (
                    "1",
                    "true",
                    "yes",
                    "on",
                )
                break

        # CA certificate (support both aliases)
        if "ca" in params:
            config.ca_cert = params["ca"][0]
        elif "ca_cert" in params:
            config.ca_cert = params["ca_cert"][0]

        # Client certificate (support both aliases)
        if "cert" in params:
            config.client_cert = params["cert"][0]
        elif "client_cert" in params:
            config.client_cert = params["client_cert"][0]

        # Client key (support both aliases)
        if "key" in params:
            config.client_key = params["key"][0]
        elif "client_key" in params:
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

        # Always set server_name for SNI (required on aarch64 even with skip_verify)
        if self.config.server_name:
            configuration.server_name = self.config.server_name
        else:
            configuration.server_name = self.config.host

        if self.config.skip_verify:
            configuration.verify_mode = 0
        else:
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

        # Server uses transparent oneof (fd(null)) so encode QuicClientMessage directly
        data = msg.SerializeToString()

        # 4-byte big-endian length prefix
        frame = struct.pack(">I", len(data)) + data
        self._protocol.write_to_stream(self._stream_id, frame)

    async def _read_message(self, read_timeout: float = 30.0) -> QuicServerMessage:
        """Read a length-prefixed protobuf message with timeout."""
        if not self._connected:
            raise TransportError("Not connected")

        # Read 4-byte length prefix
        while len(self._buffer) < 4:
            try:
                data = await asyncio.wait_for(
                    self._reader_queue.get(), timeout=read_timeout
                )
            except asyncio.TimeoutError:
                raise TransportError("Timeout reading message length")
            if data is None:
                raise TransportError("Stream closed")
            self._buffer += data

        msg_len = struct.unpack(">I", self._buffer[:4])[0]
        total_needed = 4 + msg_len

        # Read message body
        while len(self._buffer) < total_needed:
            try:
                data = await asyncio.wait_for(
                    self._reader_queue.get(), timeout=read_timeout
                )
            except asyncio.TimeoutError:
                raise TransportError("Timeout reading message body")
            if data is None:
                raise TransportError("Stream closed")
            self._buffer += data

        msg_data = self._buffer[4:total_needed]
        self._buffer = self._buffer[total_needed:]

        # Server uses transparent oneof (fd(null)) so decode QuicServerMessage directly
        message = QuicServerMessage()
        message.ParseFromString(msg_data)
        return message

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

        # Server uses transparent oneof (fd(null)) so decode QuicServerMessage directly
        message = QuicServerMessage()
        message.ParseFromString(msg_data)
        return message

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

    def _fetch_server_cert(self, host: str, port: int) -> bytes:
        """Fetch the server's TLS certificate for skip_verify connections.

        Connects with verification disabled to retrieve the server's
        certificate, then uses it as a trusted root CA so grpcio can
        complete the TLS handshake without system CA validation.

        Negotiates ALPN 'h2' so the server's ALPN callback succeeds
        (required by gRPC/HTTP2 servers that enforce ALPN selection).
        """
        import socket
        import ssl as stdlib_ssl

        ctx = stdlib_ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = stdlib_ssl.CERT_NONE
        ctx.set_alpn_protocols(["h2"])

        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert_der = ssock.getpeercert(binary_form=True)
                if cert_der is None:
                    raise TransportError("No certificate from server")
                pem = stdlib_ssl.DER_cert_to_PEM_cert(cert_der).encode()
                # Extract the CN for ssl_target_name_override
                cn = None
                try:
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
                        f.write(pem)
                        f.flush()
                        parsed = stdlib_ssl._ssl._test_decode_cert(f.name)
                    os.unlink(f.name)
                    for rdn in parsed.get("subject", ()):
                        for attr_type, attr_value in rdn:
                            if attr_type == "commonName":
                                cn = attr_value
                except Exception:
                    pass
                return pem, cn

    async def connect(self) -> None:
        """Establish gRPC connection."""
        if self._connected:
            return

        import grpc

        from .proto import GeodeServiceStub

        target = f"{self.config.host}:{self.config.port}"

        if self.config.tls_enabled:
            if self.config.skip_verify:
                # TLS with verification disabled: fetch the server's
                # self-signed cert and trust it directly.
                server_cert = None
                cert_cn = None
                try:
                    server_cert, cert_cn = self._fetch_server_cert(
                        self.config.host, self.config.port
                    )
                except Exception:
                    pass

                if server_cert:
                    credentials = grpc.ssl_channel_credentials(
                        root_certificates=server_cert
                    )
                    # Use the cert's CN for hostname override so TLS
                    # verification passes with self-signed certs.
                    # Prefer CN from the actual cert since we're trusting it.
                    override = cert_cn or self.config.server_name or self.config.host
                    options = [
                        ("grpc.ssl_target_name_override", override),
                    ]
                    self._channel = grpc.aio.secure_channel(
                        target, credentials, options=options
                    )
                else:
                    # Fallback to insecure if cert fetch fails
                    self._channel = grpc.aio.insecure_channel(target)
            else:
                # Secure channel with full verification
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
                    credentials = grpc.ssl_channel_credentials(
                        root_certificates=ca_cert
                    )

                self._channel = grpc.aio.secure_channel(target, credentials)
        else:
            # Plaintext channel (no TLS)
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

    async def hello(self, request: HelloRequest) -> HelloResponse:
        """Send HELLO handshake via gRPC."""
        try:
            response = await self._stub.Handshake(request)
            if response.success:
                self._session_id = response.session_id
            return response
        except Exception as e:
            if "grpc" in type(e).__module__:
                raise TransportConnectionError(
                    str(e), "grpc", self.config.host, self.config.port
                )
            raise

    async def execute(self, request: ExecuteRequest) -> QuicServerMessage:
        """Execute a query via gRPC streaming.

        Returns a QuicServerMessage wrapping the ExecutionResponse for
        compatibility with the QUIC transport interface.
        """
        try:
            # Execute returns a stream - get first response
            stream = self._stub.Execute(request)
            response = await stream.read()
            if response is None:
                raise TransportError("No response from server")
            # Wrap typed response into QuicServerMessage for caller compatibility
            return QuicServerMessage(execute=response)
        except Exception as e:
            if "grpc" in type(e).__module__:
                raise TransportConnectionError(
                    str(e), "grpc", self.config.host, self.config.port
                )
            raise

    async def pull(self, request: PullRequest) -> QuicServerMessage:
        """Pull more results via gRPC.

        Note: The canonical gRPC service does not define a Pull RPC.
        Pull is a QUIC-only concept. For gRPC, additional results come
        from the Execute stream. This method raises NotImplementedError.
        """
        raise NotImplementedError(
            "Pull is not available via gRPC. Use the Execute stream instead."
        )

    async def ping(self) -> bool:
        """Ping the server via gRPC."""
        try:
            response = await self._stub.Ping(PingRequest())
            return response.ok
        except Exception:
            return False

    async def begin(self, request: BeginRequest) -> QuicServerMessage:
        """Begin a transaction via gRPC.

        Returns a QuicServerMessage wrapping the BeginResponse for
        compatibility with the QUIC transport interface.
        """
        try:
            response = await self._stub.Begin(request)
            return QuicServerMessage(begin=response)
        except Exception as e:
            if "grpc" in type(e).__module__:
                raise TransportConnectionError(
                    str(e), "grpc", self.config.host, self.config.port
                )
            raise

    async def commit(self, request: CommitRequest) -> QuicServerMessage:
        """Commit a transaction via gRPC.

        Returns a QuicServerMessage wrapping the CommitResponse for
        compatibility with the QUIC transport interface.
        """
        try:
            response = await self._stub.Commit(request)
            return QuicServerMessage(commit=response)
        except Exception as e:
            if "grpc" in type(e).__module__:
                raise TransportConnectionError(
                    str(e), "grpc", self.config.host, self.config.port
                )
            raise

    async def rollback(self, request: RollbackRequest) -> QuicServerMessage:
        """Rollback a transaction via gRPC.

        Returns a QuicServerMessage wrapping the RollbackResponse for
        compatibility with the QUIC transport interface.
        """
        try:
            response = await self._stub.Rollback(request)
            return QuicServerMessage(rollback=response)
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

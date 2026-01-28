"""
Pytest configuration and fixtures for integration tests.

Supports two modes:
1. External server: Set GEODE_HOST and GEODE_PORT environment variables
   to connect to an already-running Geode server (no Docker).
2. Docker mode: If env vars are not set, starts a Docker container.
"""

import atexit
import os
import subprocess
import time
from collections.abc import Generator
from typing import Optional

import pytest

from geode_client import Client, ConnectionPool

# Test configuration
GEODE_IMAGE = "registry.gitlab.com/devnw/geode/geode:latest"
DEFAULT_GEODE_PORT = 3141
CONTAINER_STARTUP_TIMEOUT = 60  # seconds
CONTAINER_NAME = "geode-python-test"

# Check for external server configuration via environment variables
_EXTERNAL_HOST = os.environ.get("GEODE_HOST")
_EXTERNAL_PORT = os.environ.get("GEODE_PORT")


def _find_available_port() -> int:
    """Find an available UDP port."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_server_ready(container_name: str, timeout: int = 60) -> bool:
    """Wait for 'Server ready' in container logs."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = subprocess.run(
                ["docker", "logs", container_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "Server ready" in result.stdout or "Server ready" in result.stderr:
                return True
            # Also check for listening message
            if "Listening on" in result.stdout or "Listening on" in result.stderr:
                # Give it a moment to fully initialize
                time.sleep(0.5)
                return True
        except subprocess.TimeoutExpired:
            pass
        time.sleep(0.5)
    return False


def _cleanup_container(container_name: str) -> None:
    """Remove container if it exists."""
    try:
        subprocess.run(
            ["docker", "rm", "-f", container_name], capture_output=True, timeout=10
        )
    except Exception:
        pass


class GeodeContainer:
    """
    Manages a Geode Docker container for integration testing.

    Since Geode uses QUIC over UDP, we use Docker directly rather than
    testcontainers, which has better support for TCP.
    """

    def __init__(self, image: str = GEODE_IMAGE, port: int = DEFAULT_GEODE_PORT):
        self.image = image
        self.container_port = port
        self.host_port: Optional[int] = None
        self.container_name = f"{CONTAINER_NAME}-{os.getpid()}"
        self._started = False

    def start(self) -> "GeodeContainer":
        """Start the Geode container."""
        if self._started:
            return self

        # Clean up any existing container with same name
        _cleanup_container(self.container_name)

        # Find available port
        self.host_port = _find_available_port()

        # Pull image if needed
        subprocess.run(["docker", "pull", self.image], capture_output=True, timeout=300)

        # Start container with UDP port mapping
        # Note: Docker requires -p host:container/udp for UDP ports
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            self.container_name,
            "-p",
            f"{self.host_port}:{self.container_port}/udp",
            self.image,
            "serve",
            "--listen",
            f"0.0.0.0:{self.container_port}",
            "--log-level",
            "info",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start container: {result.stderr}")

        # Wait for server to be ready
        if not _wait_for_server_ready(self.container_name, CONTAINER_STARTUP_TIMEOUT):
            logs = subprocess.run(
                ["docker", "logs", self.container_name], capture_output=True, text=True
            )
            _cleanup_container(self.container_name)
            raise RuntimeError(
                f"Container failed to start. Logs:\n{logs.stdout}\n{logs.stderr}"
            )

        self._started = True
        return self

    def stop(self) -> None:
        """Stop and remove the container."""
        if self._started:
            _cleanup_container(self.container_name)
            self._started = False

    def get_host(self) -> str:
        """Get the host address for connecting to the container."""
        return "127.0.0.1"

    def get_port(self) -> int:
        """Get the mapped host port."""
        if self.host_port is None:
            raise RuntimeError("Container not started")
        return self.host_port

    def __enter__(self) -> "GeodeContainer":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


# Module-scoped container to share across all tests in a session
_container: Optional[GeodeContainer] = None


def _using_external_server() -> bool:
    """Check if we're configured to use an external server."""
    return _EXTERNAL_HOST is not None and _EXTERNAL_PORT is not None


def _get_or_create_container() -> GeodeContainer:
    """Get existing container or create new one."""
    global _container
    if _container is None:
        _container = GeodeContainer()
        _container.start()
    return _container


@pytest.fixture(scope="session")
def geode_container() -> Generator[Optional[GeodeContainer], None, None]:
    """
    Session-scoped fixture that provides a running Geode container.

    If GEODE_HOST and GEODE_PORT environment variables are set,
    no container is started (uses external server).
    Otherwise, starts a Docker container.
    """
    if _using_external_server():
        # Using external server, no container needed
        yield None
    else:
        container = _get_or_create_container()
        yield container
        # Don't stop here - let atexit handle it for test re-runs


@pytest.fixture(scope="session")
def geode_host(geode_container: Optional[GeodeContainer]) -> str:
    """Get the Geode server host."""
    if _using_external_server():
        return _EXTERNAL_HOST
    return geode_container.get_host()


@pytest.fixture(scope="session")
def geode_port(geode_container: Optional[GeodeContainer]) -> int:
    """Get the Geode server port."""
    if _using_external_server():
        return int(_EXTERNAL_PORT)
    return geode_container.get_port()


@pytest.fixture
def client(geode_host: str, geode_port: int) -> Client:
    """
    Create a Geode client configured for the test container.

    This is a function-scoped fixture so each test gets a fresh client.
    """
    return Client(
        host=geode_host,
        port=geode_port,
        skip_verify=True,  # Test container uses self-signed certs
    )


@pytest.fixture
async def connection(client: Client):
    """
    Provide an async connection for tests.

    Automatically closes the connection after the test.
    """
    async with client.connection() as conn:
        yield conn


@pytest.fixture
async def pool(geode_host: str, geode_port: int):
    """
    Provide a connection pool for tests.

    Automatically closes the pool after the test.
    """
    pool = ConnectionPool(
        host=geode_host,
        port=geode_port,
        min_size=2,
        max_size=5,
        skip_verify=True,
    )
    async with pool:
        yield pool


# Cleanup on exit
@atexit.register
def _cleanup_on_exit():
    """Clean up container when Python exits (only if we started one)."""
    global _container
    if _container is not None and not _using_external_server():
        _container.stop()
        _container = None


# Pytest configuration
def pytest_configure(config):
    """Register integration marker."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires Geode server or Docker)",
    )


def pytest_collection_modifyitems(config, items):
    """Add integration marker to all tests in this directory."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

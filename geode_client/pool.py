"""
Connection pooling for Geode QUIC connections.

Provides efficient connection reuse for concurrent workloads.
"""

import asyncio
from typing import Optional

from .client import Client, Connection


class ConnectionPool:
    """
    Asynchronous connection pool for Geode.

    Manages a pool of QUIC connections for efficient reuse across
    concurrent tasks.

    Example:
        pool = ConnectionPool(
            host="localhost",
            port=8443,
            min_size=2,
            max_size=10,
        )

        async with pool:
            async with pool.acquire() as conn:
                page, _ = await conn.query("RETURN 1")
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3141,
        min_size: int = 1,
        max_size: int = 3,
        timeout: float = 30.0,
        **kwargs,
    ):
        """
        Initialize connection pool.

        Args:
            host: Server hostname
            port: Server port
            min_size: Minimum number of connections to maintain
            max_size: Maximum number of connections
            timeout: Timeout for acquiring a connection (seconds)
            **kwargs: Additional connection parameters
        """
        self.client = Client(host, port, **kwargs)
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout

        self._pool: asyncio.Queue[Connection] = asyncio.Queue(maxsize=max_size)
        self._size = 0
        self._lock = asyncio.Lock()
        self._closed = False
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the pool by creating minimum connections."""
        if self._initialized:
            return

        for _ in range(self.min_size):
            conn = await self._create_connection()
            await self._pool.put(conn)

        self._initialized = True

    async def _create_connection(self) -> Connection:
        """Create a new connection."""
        async with self._lock:
            if self._size >= self.max_size:
                raise RuntimeError(
                    f"Connection pool is full (max_size={self.max_size})"
                )
            self._size += 1

        try:
            conn = await self.client.connect()
            return conn
        except Exception:
            async with self._lock:
                self._size -= 1
            raise

    def acquire(self) -> "PooledConnection":
        """
        Acquire a connection from the pool.

        Returns:
            PooledConnection context manager

        Raises:
            asyncio.TimeoutError: If timeout is reached
            RuntimeError: If pool is closed

        Example:
            async with pool.acquire() as conn:
                page, _ = await conn.query("RETURN 1")
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        return PooledConnection(self)

    async def _acquire(self) -> Connection:
        """Internal method to acquire a connection."""
        # Ensure pool is initialized
        if not self._initialized:
            await self.initialize()

        try:
            # Try to get an existing connection
            conn = self._pool.get_nowait()
            return conn
        except asyncio.QueueEmpty:
            pass

        # No connection available, try to create a new one
        if self._size < self.max_size:
            return await self._create_connection()

        # Wait for a connection to become available
        return await asyncio.wait_for(self._pool.get(), timeout=self.timeout)

    async def _release(self, conn: Connection) -> None:
        """Internal method to release a connection back to the pool."""
        if self._closed:
            await conn.close()
            async with self._lock:
                self._size -= 1
            return

        try:
            self._pool.put_nowait(conn)
        except asyncio.QueueFull:
            # Pool is full, close the connection
            await conn.close()
            async with self._lock:
                self._size -= 1

    async def close(self) -> None:
        """Close all connections in the pool."""
        if self._closed:
            return

        self._closed = True

        # Close all connections
        connections = []
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                connections.append(conn)
            except asyncio.QueueEmpty:
                break

        # Close all connections concurrently
        await asyncio.gather(
            *[conn.close() for conn in connections],
            return_exceptions=True,
        )

        self._size = 0
        self._initialized = False

    async def __aenter__(self) -> "ConnectionPool":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @property
    def size(self) -> int:
        """Current pool size."""
        return self._size

    @property
    def available(self) -> int:
        """Number of available connections in pool."""
        return self._pool.qsize()


class PooledConnection:
    """
    Context manager for pooled connections.

    Automatically returns connection to pool when done.
    """

    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.conn: Optional[Connection] = None

    async def __aenter__(self) -> Connection:
        """Acquire connection from pool."""
        self.conn = await self.pool._acquire()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release connection back to pool."""
        if self.conn:
            # Only release healthy connections
            if exc_type is None:
                await self.pool._release(self.conn)
            else:
                # Connection had an error, close it
                try:
                    await self.conn.close()
                except Exception:
                    pass
                async with self.pool._lock:
                    self.pool._size -= 1

            self.conn = None


# Convenience function
async def create_pool(
    host: str = "127.0.0.1",
    port: int = 3141,
    min_size: int = 1,
    max_size: int = 3,
    **kwargs,
) -> ConnectionPool:
    """
    Create and initialize a connection pool.

    Args:
        host: Server hostname
        port: Server port
        min_size: Minimum pool size
        max_size: Maximum pool size
        **kwargs: Additional connection parameters

    Returns:
        Initialized ConnectionPool

    Example:
        pool = await create_pool(host="localhost", max_size=20)
        async with pool.acquire() as conn:
            page, _ = await conn.query("RETURN 1")
        await pool.close()
    """
    pool = ConnectionPool(host, port, min_size, max_size, **kwargs)
    await pool.initialize()
    return pool

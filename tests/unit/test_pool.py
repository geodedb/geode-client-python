"""Unit tests for Geode connection pool."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from geode_client import ConnectionPool
from geode_client.pool import PooledConnection, create_pool


class TestConnectionPoolCreation:
    """Tests for ConnectionPool creation."""

    def test_creation_defaults(self):
        """Test pool creation with defaults."""
        pool = ConnectionPool()
        assert pool.min_size == 2
        assert pool.max_size == 10
        assert pool.timeout == 30.0

    def test_creation_custom_size(self):
        """Test pool creation with custom sizes."""
        pool = ConnectionPool(min_size=5, max_size=50)
        assert pool.min_size == 5
        assert pool.max_size == 50

    def test_creation_custom_host_port(self):
        """Test pool creation with custom host/port."""
        pool = ConnectionPool(host="geode.example.com", port=9999)
        assert pool.client.host == "geode.example.com"
        assert pool.client.port == 9999

    def test_creation_timeout(self):
        """Test pool creation with custom timeout."""
        pool = ConnectionPool(timeout=60.0)
        assert pool.timeout == 60.0

    def test_creation_extra_kwargs(self):
        """Test pool passes extra kwargs to client."""
        pool = ConnectionPool(
            host="localhost",
            port=3141,
            skip_verify=True,
            page_size=500
        )
        assert pool.client.config["skip_verify"] is True
        assert pool.client.config["page_size"] == 500


class TestConnectionPoolProperties:
    """Tests for ConnectionPool properties."""

    def test_size_initial(self):
        """Test initial pool size is 0."""
        pool = ConnectionPool()
        assert pool.size == 0

    def test_available_initial(self):
        """Test initial available is 0."""
        pool = ConnectionPool()
        assert pool.available == 0


class TestConnectionPoolConfiguration:
    """Tests for pool configuration passthrough."""

    def test_config_passthrough(self):
        """Test configuration is passed to client."""
        pool = ConnectionPool(
            host="test.local",
            port=1234,
            ca_cert="/path/to/ca.crt",
            client_cert="/path/to/client.crt",
            client_key="/path/to/client.key",
            skip_verify=False,
            server_name="sni.test.local",
        )
        config = pool.client.config
        assert config["host"] == "test.local"
        assert config["port"] == 1234
        assert config["ca_cert"] == "/path/to/ca.crt"
        assert config["client_cert"] == "/path/to/client.crt"
        assert config["client_key"] == "/path/to/client.key"
        assert config["skip_verify"] is False
        assert config["server_name"] == "sni.test.local"


class TestConnectionPoolAsync:
    """Async tests for ConnectionPool."""

    @pytest.mark.asyncio
    async def test_initialize_creates_connections(self):
        """Test initialize creates min_size connections."""
        with patch.object(ConnectionPool, '_create_connection') as mock_create:
            mock_conn = AsyncMock()
            mock_create.return_value = mock_conn

            pool = ConnectionPool(min_size=3, max_size=10)
            await pool.initialize()

            assert mock_create.call_count == 3
            assert pool._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test initialize is idempotent."""
        with patch.object(ConnectionPool, '_create_connection') as mock_create:
            mock_conn = AsyncMock()
            mock_create.return_value = mock_conn

            pool = ConnectionPool(min_size=2)
            await pool.initialize()
            await pool.initialize()  # Second call

            # Should only create connections once
            assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_acquire_initializes_pool(self):
        """Test acquire initializes pool if not initialized."""
        with patch.object(ConnectionPool, '_create_connection') as mock_create:
            mock_conn = AsyncMock()
            mock_create.return_value = mock_conn

            pool = ConnectionPool(min_size=2)
            assert not pool._initialized

            # acquire() returns PooledConnection, initialization happens in __aenter__
            pooled = pool.acquire()
            assert isinstance(pooled, PooledConnection)
            # Initialization happens when entering the context manager
            async with pooled:
                assert pool._initialized

    @pytest.mark.asyncio
    async def test_acquire_returns_pooled_connection(self):
        """Test acquire returns PooledConnection."""
        with patch.object(ConnectionPool, '_create_connection') as mock_create:
            mock_conn = AsyncMock()
            mock_create.return_value = mock_conn

            pool = ConnectionPool(min_size=1)
            result = pool.acquire()

            assert isinstance(result, PooledConnection)
            assert result.pool is pool

    def test_acquire_fails_when_closed(self):
        """Test acquire raises when pool is closed."""
        pool = ConnectionPool()
        pool._closed = True

        with pytest.raises(RuntimeError, match="closed"):
            pool.acquire()

    @pytest.mark.asyncio
    async def test_close_closes_connections(self):
        """Test close closes all connections."""
        mock_conn1 = AsyncMock()
        mock_conn2 = AsyncMock()

        pool = ConnectionPool(min_size=2, max_size=5)
        pool._initialized = True
        pool._size = 2
        await pool._pool.put(mock_conn1)
        await pool._pool.put(mock_conn2)

        await pool.close()

        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()
        assert pool._closed is True
        assert pool._size == 0

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Test close is idempotent."""
        pool = ConnectionPool()
        pool._closed = True

        # Should not raise
        await pool.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        with patch.object(ConnectionPool, '_create_connection') as mock_create:
            mock_conn = AsyncMock()
            mock_create.return_value = mock_conn

            pool = ConnectionPool(min_size=1)

            async with pool as p:
                assert p is pool
                assert p._initialized

            assert pool._closed

    @pytest.mark.asyncio
    async def test_release_returns_connection(self):
        """Test _release returns connection to pool."""
        mock_conn = AsyncMock()

        pool = ConnectionPool(min_size=0, max_size=5)
        pool._initialized = True
        pool._size = 1

        await pool._release(mock_conn)

        assert pool.available == 1
        assert await pool._pool.get() is mock_conn

    @pytest.mark.asyncio
    async def test_release_closes_when_pool_closed(self):
        """Test _release closes connection when pool is closed."""
        mock_conn = AsyncMock()

        pool = ConnectionPool()
        pool._closed = True
        pool._size = 1

        await pool._release(mock_conn)

        mock_conn.close.assert_called_once()
        assert pool._size == 0


class TestPooledConnection:
    """Tests for PooledConnection context manager."""

    @pytest.mark.asyncio
    async def test_acquires_and_releases(self):
        """Test PooledConnection acquires and releases connection."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool._acquire = AsyncMock(return_value=mock_conn)
        mock_pool._release = AsyncMock()

        pooled = PooledConnection(mock_pool)

        async with pooled as conn:
            assert conn is mock_conn

        mock_pool._acquire.assert_called_once()
        mock_pool._release.assert_called_once_with(mock_conn)

    @pytest.mark.asyncio
    async def test_closes_on_exception(self):
        """Test PooledConnection closes connection on exception."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool._acquire = AsyncMock(return_value=mock_conn)
        mock_pool._release = AsyncMock()
        mock_pool._lock = asyncio.Lock()
        mock_pool._size = 1

        pooled = PooledConnection(mock_pool)

        with pytest.raises(ValueError):
            async with pooled:
                raise ValueError("test error")

        # Should close instead of release
        mock_conn.close.assert_called_once()
        mock_pool._release.assert_not_called()


class TestCreatePool:
    """Tests for create_pool convenience function."""

    @pytest.mark.asyncio
    async def test_creates_and_initializes(self):
        """Test create_pool creates and initializes pool."""
        with patch.object(ConnectionPool, '_create_connection') as mock_create:
            mock_conn = AsyncMock()
            mock_create.return_value = mock_conn

            pool = await create_pool(
                host="test.local",
                port=9999,
                min_size=3,
                max_size=20
            )

            assert isinstance(pool, ConnectionPool)
            assert pool._initialized
            assert mock_create.call_count == 3

            await pool.close()

    @pytest.mark.asyncio
    async def test_passes_kwargs(self):
        """Test create_pool passes kwargs to pool."""
        with patch.object(ConnectionPool, '_create_connection') as mock_create:
            mock_conn = AsyncMock()
            mock_create.return_value = mock_conn

            pool = await create_pool(
                skip_verify=True,
                page_size=2000
            )

            assert pool.client.config["skip_verify"] is True
            assert pool.client.config["page_size"] == 2000

            await pool.close()


class TestPoolConcurrency:
    """Tests for pool concurrency handling."""

    @pytest.mark.asyncio
    async def test_acquire_existing_connection(self):
        """Test _acquire returns existing connection from pool."""
        mock_conn = AsyncMock()

        pool = ConnectionPool(min_size=0, max_size=5)
        pool._initialized = True
        pool._size = 1
        await pool._pool.put(mock_conn)

        result = await pool._acquire()

        assert result is mock_conn

    @pytest.mark.asyncio
    async def test_acquire_creates_when_empty(self):
        """Test _acquire creates connection when pool is empty."""
        with patch.object(ConnectionPool, '_create_connection') as mock_create:
            mock_conn = AsyncMock()
            mock_create.return_value = mock_conn

            pool = ConnectionPool(min_size=0, max_size=5)
            pool._initialized = True

            result = await pool._acquire()

            assert result is mock_conn
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_connection_respects_max(self):
        """Test _create_connection respects max_size."""
        pool = ConnectionPool(max_size=2)
        pool._size = 2  # Already at max

        with pytest.raises(RuntimeError, match="full"):
            await pool._create_connection()

    @pytest.mark.asyncio
    async def test_acquire_waits_when_at_max(self):
        """Test _acquire waits for connection when at max size."""
        mock_conn = AsyncMock()

        pool = ConnectionPool(min_size=0, max_size=1, timeout=0.1)
        pool._initialized = True
        pool._size = 1  # At max

        # Start acquire in background (will wait)
        async def acquire_task():
            return await pool._acquire()

        task = asyncio.create_task(acquire_task())

        # Give the task a moment to start waiting
        await asyncio.sleep(0.01)

        # Release a connection
        await pool._pool.put(mock_conn)

        # Should get the connection
        result = await task
        assert result is mock_conn

    @pytest.mark.asyncio
    async def test_acquire_timeout(self):
        """Test _acquire times out when no connection available."""
        pool = ConnectionPool(min_size=0, max_size=1, timeout=0.1)
        pool._initialized = True
        pool._size = 1  # At max, no connections available

        with pytest.raises(asyncio.TimeoutError):
            await pool._acquire()


class TestPoolSizeTracking:
    """Tests for pool size tracking."""

    @pytest.mark.asyncio
    async def test_size_increases_on_create(self):
        """Test size increases when connection is created."""
        with patch('geode_client.pool.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_conn = AsyncMock()
            mock_client.connect = AsyncMock(return_value=mock_conn)
            mock_client_class.return_value = mock_client

            pool = ConnectionPool(min_size=0, max_size=5)
            initial_size = pool.size

            await pool._create_connection()

            assert pool.size == initial_size + 1

    @pytest.mark.asyncio
    async def test_size_decreases_on_release_when_closed(self):
        """Test size decreases when releasing to closed pool."""
        mock_conn = AsyncMock()

        pool = ConnectionPool()
        pool._size = 1
        pool._closed = True

        await pool._release(mock_conn)

        assert pool._size == 0

    @pytest.mark.asyncio
    async def test_size_decreases_on_close(self):
        """Test size becomes 0 after close."""
        mock_conn = AsyncMock()

        pool = ConnectionPool()
        pool._size = 3
        pool._initialized = True
        await pool._pool.put(mock_conn)

        await pool.close()

        assert pool._size == 0


class TestPoolDefaults:
    """Tests for pool default values."""

    def test_default_host(self):
        """Test default host is 127.0.0.1."""
        pool = ConnectionPool()
        assert pool.client.host == "127.0.0.1"

    def test_default_port(self):
        """Test default port is 8443."""
        pool = ConnectionPool()
        assert pool.client.port == 8443

    def test_default_min_size(self):
        """Test default min_size is 2."""
        pool = ConnectionPool()
        assert pool.min_size == 2

    def test_default_max_size(self):
        """Test default max_size is 10."""
        pool = ConnectionPool()
        assert pool.max_size == 10

    def test_default_timeout(self):
        """Test default timeout is 30.0."""
        pool = ConnectionPool()
        assert pool.timeout == 30.0

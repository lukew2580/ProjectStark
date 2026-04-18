"""
Core Engine — Connection Pooling
Generic async connection pool abstraction with aiohttp and asyncpg implementations.
Enables connection reuse, limits concurrency, provides health checks.
"""

import asyncio
import logging
from typing import Dict, Optional, Any, AsyncContextManager
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time

logger = logging.getLogger("hardwareless.connections")


@dataclass
class PoolConfig:
    """Configuration for a connection pool."""
    max_connections: int = 20
    max_idle_time_seconds: float = 300.0
    connection_timeout_seconds: float = 10.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 0.5
    health_check_interval_seconds: float = 30.0
    enable_metrics: bool = True


class PooledConnection(ABC):
    """
    A connection managed by a pool.
    Wraps raw connection with metadata (last used, age, health).
    """
    
    def __init__(self, raw: Any):
        self.raw = raw
        self.created_at = time.monotonic()
        self.last_used_at = time.monotonic()
        self.use_count = 0
        self._healthy = True
    
    def mark_used(self):
        self.last_used_at = time.monotonic()
        self.use_count += 1
    
    def mark_idle(self):
        pass  # override if needed
    
    def is_stale(self, max_idle: float) -> bool:
        return (time.monotonic() - self.last_used_at) > max_idle
    
    async def health_check(self) -> bool:
        """Quick check if connection is still alive."""
        return self._healthy
    
    async def close(self):
        """Close the underlying connection."""
        pass


class ConnectionPool(ABC):
    """
    Abstract async connection pool.
    Manages lifecycle, borrowing, returning, and health of pooled connections.
    """
    
    def __init__(self, config: PoolConfig):
        self.config = config
        self._pool: asyncio.Queue[PooledConnection] = asyncio.Queue(maxsize=config.max_connections)
        self._lock = asyncio.Lock()
        self._created_count = 0
        self._closed_count = 0
        self._health_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize pool (start background tasks)."""
        self._running = True
        if self.config.enable_metrics:
            self._health_task = asyncio.create_task(self._health_loop())
        logger.info(f"Connection pool initialized: max={self.config.max_connections}")
    
    async def shutdown(self) -> None:
        """Close all connections and stop background tasks."""
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        # Close all pooled connections
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                await conn.close()
                self._closed_count += 1
            except asyncio.QueueEmpty:
                break
        
        logger.info(f"Connection pool shut down: created={self._created_count}, closed={self._closed_count}")
    
    @abstractmethod
    async def _create_connection(self) -> PooledConnection:
        """Create a new raw connection and wrap it."""
        pass
    
    @abstractmethod
    async def _validate_connection(self, conn: PooledConnection) -> bool:
        """Check if a connection is still healthy for reuse."""
        pass
    
    async def acquire(self) -> PooledConnection:
        """
        Borrow a connection from the pool, creating a new one if needed.
        Blocks if pool exhausted until a connection is returned or timeout.
        """
        # Try existing idle connection first
        try:
            conn = self._pool.get_nowait()
            # Re-validate
            if not await self._validate_connection(conn):
                await conn.close()
                self._closed_count += 1
                return await self.acquire()
            conn.mark_used()
            return conn
        except asyncio.QueueEmpty:
            pass
        
        # Need new connection (respect max size)
        async with self._lock:
            if self._created_count < self.config.max_connections:
                try:
                    raw_conn = await self._raw_create_with_retry()
                    conn = self._wrap(raw_conn)
                    self._created_count += 1
                    conn.mark_used()
                    return conn
                except Exception as e:
                    logger.error(f"Failed to create connection: {e}")
                    raise
        
        # Pool exhausted — wait for a returned connection
        try:
            conn = await asyncio.wait_for(
                self._pool.get(),
                timeout=self.config.connection_timeout_seconds
            )
            if await self._validate_connection(conn):
                conn.mark_used()
                return conn
            else:
                await conn.close()
                self._closed_count += 1
                return await self.acquire()
        except asyncio.TimeoutError:
            raise RuntimeError("Connection pool exhausted — all connections in use")
    
    async def release(self, conn: PooledConnection) -> None:
        """Return a connection to the pool."""
        if not await self._validate_connection(conn):
            await conn.close()
            self._closed_count += 1
            return
        
        if self._pool.full():
            # Pool full — just close it
            await conn.close()
            self._closed_count += 1
            return
        
        conn.mark_idle()
        try:
            self._pool.put_nowait(conn)
        except asyncio.QueueFull:
            await conn.close()
            self._closed_count += 1
    
    async def _raw_create_with_retry(self) -> Any:
        """Create raw connection with retry logic."""
        last_exc = None
        for attempt in range(self.config.retry_attempts):
            try:
                return await self._create_single_connection()
            except Exception as e:
                last_exc = e
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
        raise RuntimeError(f"Failed to create connection after {self.config.retry_attempts} attempts") from last_exc
    
    @abstractmethod
    async def _create_single_connection(self) -> Any:
        """Create a single raw connection (single attempt)."""
        pass
    
    def _wrap(self, raw: Any) -> PooledConnection:
        """Wrap raw connection in a PooledConnection subclass."""
        raise NotImplementedError
    
    async def _health_loop(self):
        """Background task that periodically culls stale connections."""
        while self._running:
            await asyncio.sleep(self.config.health_check_interval_seconds)
            try:
                await self._cull_stale()
            except Exception as e:
                logger.warning(f"Health check error: {e}")
    
    async def _cull_stale(self):
        """Remove stale idle connections from the pool."""
        culled = 0
        # Pull all connections out, check, and requeue good ones
        connections: List[PooledConnection] = []
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                connections.append(conn)
            except asyncio.QueueEmpty:
                break
        
        for conn in connections:
            if conn.is_stale(self.config.max_idle_time_seconds):
                await conn.close()
                self._closed_count += 1
                culled += 1
            elif not await self._validate_connection(conn):
                await conn.close()
                self._closed_count += 1
                culled += 1
            else:
                try:
                    self._pool.put_nowait(conn)
                except asyncio.QueueFull:
                    await conn.close()
                    self._closed_count += 1
                    culled += 1
        
        if culled:
            logger.debug(f"Connection pool culled {culled} stale connections")


class AIOHTTPConnectionPool(ConnectionPool):
    """
    HTTP connection pool using aiohttp.ClientSession.
    Uses connector pooling internally, but wraps for unified interface.
    """
    
    def __init__(
        self,
        base_url: str,
        config: Optional[PoolConfig] = None,
        **session_kwargs: Any,
    ):
        super().__init__(config or PoolConfig())
        self.base_url = base_url
        self.session_kwargs = session_kwargs
        self._session: Optional[Any] = None  # aiohttp.ClientSession
        self._connector: Optional[Any] = None  # aiohttp.TCPConnector
    
    async def initialize(self) -> None:
        """Create shared aiohttp.ClientSession with connection pool."""
        try:
            import aiohttp
        except ImportError:
            raise RuntimeError("aiohttp is required for AIOHTTPConnectionPool")
        
        limit = self.config.max_connections
        
        self._connector = aiohttp.TCPConnector(
            limit=limit,
            ttl_dns_cache=300,
            force_close=False,
            enable_cleanup_closed=True,
        )
        
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=aiohttp.ClientTimeout(total=self.config.connection_timeout_seconds),
            **self.session_kwargs,
        )
        
        await super().initialize()
        logger.info(f"AIOHTTP pool initialized: base_url={self.base_url}, limit={limit}")
    
    def _wrap(self, raw: Any) -> PooledConnection:
        """Wrap an aiohttp response or session — we actually reuse session, so return marker."""
        class DummyConn(PooledConnection):
            def __init__(self, session):
                super().__init__(session)
            async def close(self):
                pass  # session closes in shutdown
            async def health_check(self) -> bool:
                return self.raw is not None and not self.raw.closed
        return DummyConn(self._session)
    
    async def _create_single_connection(self) -> Any:
        """Return the shared session (connections managed by connector)."""
        return self._session
    
    async def _validate_connection(self, conn: PooledConnection) -> bool:
        """Check session is still open."""
        return await conn.health_check()
    
    async def shutdown(self) -> None:
        """Close session and connector."""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector:
            await self._connector.close()
        await super().shutdown()
    
    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """
        Perform an HTTP request using the pooled session.
        Returns aiohttp.ClientResponse.
        """
        if not self._session:
            raise RuntimeError("Pool not initialized")
        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        return await self._session.request(method, url, **kwargs)


class GenericPoolManager:
    """
    Manages multiple named connection pools (e.g., per translation backend host).
    """
    
    def __init__(self):
        self._pools: Dict[str, ConnectionPool] = {}
        self._configs: Dict[str, PoolConfig] = {}
    
    def register_pool(self, name: str, pool: ConnectionPool) -> None:
        self._pools[name] = pool
    
    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        return self._pools.get(name)
    
    async def initialize_all(self) -> None:
        for name, pool in self._pools.items():
            try:
                await pool.initialize()
                logger.info(f"Pool initialized: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize pool {name}: {e}")
    
    async def shutdown_all(self) -> None:
        for name, pool in self._pools.items():
            try:
                await pool.shutdown()
                logger.info(f"Pool shut down: {name}")
            except Exception as e:
                logger.error(f"Error shutting down pool {name}: {e}")
    
    def configure(self, name: str, config: PoolConfig) -> None:
        self._configs[name] = config
    
    async def health_all(self) -> Dict[str, Any]:
        """Check health of all pools."""
        report = {}
        for name, pool in self._pools.items():
            created = pool._created_count if hasattr(pool, '_created_count') else 0
            idle = pool._pool.qsize() if hasattr(pool, '_pool') else 0
            report[name] = {
                "created": created,
                "idle": idle,
                "max": pool.config.max_connections if hasattr(pool, 'config') else 'unknown',
            }
        return report


# Singleton manager
_global_pool_manager: Optional[GenericPoolManager] = None

def get_pool_manager() -> GenericPoolManager:
    global _global_pool_manager
    if _global_pool_manager is None:
        _global_pool_manager = GenericPoolManager()
    return _global_pool_manager

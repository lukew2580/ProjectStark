"""
Core Engine — Connections Package
Connection pooling and request batching.
"""

from .pool import (
    PoolConfig,
    PooledConnection,
    ConnectionPool,
    AIOHTTPConnectionPool,
    GenericPoolManager,
    get_pool_manager,
)
from .batcher import (
    BatchItem,
    BatchConfig,
    RequestBatcher,
    TranslationBatcher,
    batched,
)

__all__ = [
    # Pooling
    "PoolConfig",
    "PooledConnection",
    "ConnectionPool",
    "AIOHTTPConnectionPool",
    "GenericPoolManager",
    "get_pool_manager",
    # Batching
    "BatchItem",
    "BatchConfig",
    "RequestBatcher",
    "TranslationBatcher",
    "batched",
]

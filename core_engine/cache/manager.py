"""
Core Engine — Caching System
Multi-tier async cache: in-memory LRU → Redis cluster → disk.
Provides cache-aside pattern, warming hooks, TTL, eviction, metrics.
"""

import asyncio
import pickle
import hashlib
import json
import logging
import os
import time
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from collections import OrderedDict
import pickle

logger = logging.getLogger("hardwareless.cache")


@dataclass
class CacheConfig:
    """Configuration for a cache backend."""
    max_size: int = 10000          # Max items (LRU)
    default_ttl_seconds: Optional[int] = 3600  # Default TTL (None = forever)
    enable_metrics: bool = True
    disk_path: Optional[str] = None
    redis_url: Optional[str] = None
    redis_prefix: str = "hdc:"


class CacheBackend(ABC):
    """
    Abstract cache backend.
    All implementations must be async-safe.
    """
    
    async def initialize(self) -> None:
        """One-time startup (e.g., connect to Redis)."""
        pass
    
    async def shutdown(self) -> None:
        """Clean shutdown (close connections, flush disk)."""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache. Returns None if missing or expired."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set a value with optional TTL. Returns success."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key. Returns whether deleted."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists (without loading value)."""
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        """Remove all keys. Returns count removed."""
        pass
    
    async def flush(self) -> None:
        """Ensure pending writes are persisted."""
        pass
    
    async def stats(self) -> Dict[str, Any]:
        """Return backend statistics."""
        return {}
    
    def _make_key(self, namespace: str, identifier: str) -> str:
        """Construct a namespaced cache key."""
        safe_id = hashlib.md5(identifier.encode()).hexdigest()[:16]
        return f"{namespace}:{safe_id}"


class MemoryLRUBackend(CacheBackend):
    """
    In-memory LRU cache using OrderedDict.
    Fastest tier, bounded memory, evicts on size pressure.
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._store: OrderedDict[str, Tuple[Any, float]] = OrderedDict()  # key → (value, expiry)
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._evictions = 0
    
    async def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            self._misses += 1
            return None
        
        value, expiry = self._store[key]
        if expiry is not None and time.time() > expiry:
            del self._store[key]
            self._misses += 1
            return None
        
        # Move to end (most recently used)
        self._store.move_to_end(key)
        self._hits += 1
        return value
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        self._sets += 1
        expiry = (time.time() + ttl_seconds) if ttl_seconds is not None else None
        
        # Evict if at capacity and adding new key
        if key not in self._store and len(self._store) >= self.config.max_size:
            # Evict LRU (first item)
            oldest = next(iter(self._store))
            del self._store[oldest]
            self._evictions += 1
        
        self._store[key] = (value, expiry)
        # Move to end (most recently used)
        self._store.move_to_end(key)
        
        # Periodic cleanup of expired entries (every ~100 sets)
        if self._sets % 100 == 0:
            self._purge_expired()
        
        return True
    
    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        if key not in self._store:
            return False
        _, expiry = self._store[key]
        if expiry is not None and time.time() > expiry:
            del self._store[key]
            return False
        return True
    
    async def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count
    
    async def stats(self) -> Dict[str, Any]:
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests) if total_requests else 0.0
        return {
            "backend": "memory-lru",
            "size": len(self._store),
            "max_size": self.config.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "sets": self._sets,
            "evictions": self._evictions,
        }
    
    def _purge_expired(self):
        """Remove expired entries."""
        now = time.time()
        to_delete = [k for k, (_, exp) in self._store.items() if exp is not None and exp <= now]
        for k in to_delete:
            del self._store[k]


class RedisClusterBackend(CacheBackend):
    """
    Redis cluster backend using redis-py (async).
    Falls back gracefully if Redis unavailable.
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._client = None
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._errors = 0
    
    async def initialize(self) -> None:
        if not self.config.redis_url:
            logger.warning("Redis cache configured but redis_url not set")
            return
        
        try:
            import redis.asyncio as redis
            self._client = redis.from_url(self.config.redis_url)
            await self._client.ping()
            logger.info(f"Redis cache connected: {self.config.redis_url}")
        except ImportError:
            logger.error("redis-py not installed; Redis cache disabled")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._client = None
            self._errors += 1
    
    async def get(self, key: str) -> Optional[Any]:
        if not self._client:
            return None
        try:
            raw = await self._client.get(self._full_key(key))
            if raw is None:
                self._misses += 1
                return None
            self._hits += 1
            return pickle.loads(raw)
        except Exception as e:
            logger.debug(f"Redis get error: {e}")
            self._errors += 1
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        if not self._client:
            return False
        try:
            raw = pickle.dumps(value)
            ex = ttl_seconds if ttl_seconds is not None else None
            await self._client.set(self._full_key(key), raw, ex=ex)
            self._sets += 1
            return True
        except Exception as e:
            logger.debug(f"Redis set error: {e}")
            self._errors += 1
            return False
    
    async def delete(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            count = await self._client.delete(self._full_key(key))
            return count > 0
        except Exception as e:
            self._errors += 1
            return False
    
    async def exists(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            return bool(await self._client.exists(self._full_key(key)))
        except Exception:
            self._errors += 1
            return False
    
    async def clear(self) -> int:
        if not self._client:
            return 0
        try:
            keys = await self._client.keys(self._full_key("*"))
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception:
            self._errors += 1
            return 0
    
    async def stats(self) -> Dict[str, Any]:
        if not self._client:
            return {"backend": "redis", "connected": False}
        try:
            info = await self._client.info()
            return {
                "backend": "redis",
                "connected": True,
                "redis_version": info.get("redis_version"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hits": self._hits,
                "misses": self._misses,
                "sets": self._sets,
                "errors": self._errors,
            }
        except Exception as e:
            return {"backend": "redis", "connected": False, "error": str(e)}
    
    def _full_key(self, key: str) -> str:
        return f"{self.config.redis_prefix}{key}"
    
    async def flush(self) -> None:
        if self._client:
            await self._client.flushdb()


class DiskCacheBackend(CacheBackend):
    """
    Disk-backed cache for large/long-lived blobs.
    Stores items as files in a cache directory.
    Uses file mtime for TTL.
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache_dir = Path(config.disk_path or "cache_disk")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._hits = 0
        self._misses = 0
    
    def _file_path(self, key: str) -> Path:
        # Use key hash as filename to avoid filesystem issues
        h = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{h}.pickle"
    
    async def get(self, key: str) -> Optional[Any]:
        path = self._file_path(key)
        if not path.exists():
            self._misses += 1
            return None
        
        try:
            mtime = path.stat().st_mtime
            # Check TTL
            ttl = self.config.default_ttl_seconds
            if ttl is not None and (time.time() - mtime) > ttl:
                path.unlink(missing_ok=True)
                self._misses += 1
                return None
            
            with open(path, "rb") as f:
                value = pickle.load(f)
            self._hits += 1
            return value
        except Exception as e:
            logger.debug(f"Disk cache read error: {e}")
            self._misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        path = self._file_path(key)
        try:
            with open(path, "wb") as f:
                pickle.dump(value, f)
            if ttl_seconds is not None:
                # Adjust file mtime to reflect TTL expiry we can't set actual expiry
                pass  # mtime naturally reflects creation time
            return True
        except Exception as e:
            logger.debug(f"Disk cache write error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        path = self._file_path(key)
        if path.exists():
            path.unlink()
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        path = self._file_path(key)
        if not path.exists():
            return False
        ttl = self.config.default_ttl_seconds
        if ttl is not None and (time.time() - path.stat().st_mtime) > ttl:
            path.unlink(missing_ok=True)
            return False
        return True
    
    async def clear(self) -> int:
        count = 0
        for path in self.cache_dir.glob("*.pickle"):
            path.unlink(missing_ok=True)
            count += 1
        return count
    
    async def stats(self) -> Dict[str, Any]:
        total_size = sum(p.stat().st_size for p in self.cache_dir.glob("*.pickle") if p.exists())
        file_count = len(list(self.cache_dir.glob("*.pickle")))
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests) if total_requests else 0.0
        return {
            "backend": "disk",
            "path": str(self.cache_dir),
            "files": file_count,
            "total_bytes": total_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
        }
    
    async def flush(self) -> None:
        await self.clear()


# Composite cache: multi-tier cascade (memory → Redis → disk → miss)
class CompositeCache(CacheBackend):
    """
    Cascading cache: query memory first, then Redis, then disk.
    Writes update all tiers (write-through).
    """
    
    def __init__(
        self,
        tiers: List[CacheBackend],
        config: CacheConfig,
    ):
        self.tiers = tiers
        self.config = config
        self._hits = 0
        self._misses = 0
        self._sets = 0
    
    async def initialize(self) -> None:
        for tier in self.tiers:
            await tier.initialize()
    
    async def shutdown(self) -> None:
        for tier in reversed(self.tiers):
            try:
                await tier.shutdown()
            except Exception as e:
                logger.warning(f"Tier shutdown error: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Check tiers in order; first hit wins."""
        for idx, tier in enumerate(self.tiers):
            value = await tier.get(key)
            if value is not None:
                # Populate higher tiers (lazy promotion)
                if idx > 0:
                    for higher in self.tiers[:idx]:
                        try:
                            await higher.set(key, value, self.config.default_ttl_seconds)
                        except Exception:
                            pass
                self._hits += 1
                return value
        self._misses += 1
        return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Write-through to all tiers."""
        self._sets += 1
        ttl = ttl_seconds or self.config.default_ttl_seconds
        success = True
        for tier in self.tiers:
            try:
                result = await tier.set(key, value, ttl)
                if not result:
                    success = False
            except Exception as e:
                logger.warning(f"Cache tier set failed: {e}")
                success = False
        return success
    
    async def delete(self, key: str) -> bool:
        """Delete from all tiers."""
        success = True
        for tier in self.tiers:
            try:
                if not await tier.delete(key):
                    success = False
            except Exception:
                success = False
        return success
    
    async def exists(self, key: str) -> bool:
        return any(await tier.exists(key) for tier in self.tiers)
    
    async def clear(self) -> int:
        total = 0
        for tier in self.tiers:
            try:
                total += await tier.clear()
            except Exception:
                pass
        return total
    
    async def stats(self) -> Dict[str, Any]:
        combined = {
            "backend": "composite",
            "levels": len(self.tiers),
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "hit_rate": round(self._hits / (self._hits + self._misses), 4) if (self._hits + self._misses) else 0.0,
            "tiers": [],
        }
        for idx, tier in enumerate(self.tiers):
            try:
                tier_stats = await tier.stats()
                combined["tiers"].append({"level": idx, **tier_stats})
            except Exception as e:
                combined["tiers"].append({"level": idx, "error": str(e)})
        return combined
    
    async def flush(self) -> None:
        for tier in self.tiers:
            try:
                await tier.flush()
            except Exception as e:
                logger.warning(f"Tier flush error: {e}")


# Cache-aside helper for common pattern
class CacheManager:
    """
    High-level cache manager with:
    - Namespaces (separate namespaces for different data types)
    - Cache warming via hooks
    - Event listeners on set/delete
    - Integrated metrics (via telemetry)
    """
    
    def __init__(self, backend: CacheBackend):
        self.backend = backend
        self._warmers: Dict[str, callable] = {}
        self._listeners: Dict[str, List[callable]] = {}
    
    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get value from named namespace."""
        full_key = self.backend._make_key(namespace, key)
        return await self.backend.get(full_key)
    
    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        warm: bool = False,
    ) -> bool:
        """Set value in named namespace. warm=True triggers warmer on miss."""
        full_key = self.backend._make_key(namespace, key)
        result = await self.backend.set(full_key, value, ttl_seconds)
        self._emit("set", namespace, key, value)
        return result
    
    async def delete(self, namespace: str, key: str) -> bool:
        full_key = self.backend._make_key(namespace, key)
        result = await self.backend.delete(full_key)
        self._emit("delete", namespace, key, None)
        return result
    
    async def get_or_load(
        self,
        namespace: str,
        key: str,
        loader: callable,
        ttl_seconds: Optional[int] = None,
    ) -> Any:
        """
        Cache-aside: try cache, call loader on miss, store result.
        `loader` is an async callable that returns the value.
        """
        cached = await self.get(namespace, key)
        if cached is not None:
            return cached
        
        # Miss — load
        value = await loader()
        if value is not None:
            await self.set(namespace, key, value, ttl_seconds=ttl_seconds)
        return value
    
    def register_warmer(self, namespace: str, warmer: callable) -> None:
        """
        Register a cache warmer function (called on startup to pre-populate).
        warmer is an async callable that returns Dict[key, value].
        """
        self._warmers[namespace] = warmer
    
    async def warm_namespace(self, namespace: str) -> int:
        """Execute warmer for a namespace; returns keys warmed."""
        if namespace not in self._warmers:
            return 0
        warmer = self._warmers[namespace]
        data = await warmer()
        count = 0
        ttl = self.config.default_ttl_seconds if hasattr(self, 'config') else None
        for key, value in data.items():
            await self.set(namespace, key, value, ttl_seconds=ttl)
            count += 1
        logger.info(f"Cache warmed namespace '{namespace}': {count} keys")
        return count
    
    def on_event(self, event: str, namespace: str, handler: callable) -> None:
        """
        Register event handler: 'set', 'delete', 'clear'.
        Handler receives (namespace, key, value) for set.
        """
        self._listeners.setdefault(event, []).append(handler)
    
    def _emit(self, event: str, namespace: str, key: str, value: Any):
        for handler in self._listeners.get(event, []):
            try:
                handler(namespace, key, value)
            except Exception:
                pass
    
    async def stats(self) -> Dict[str, Any]:
        return await self.backend.stats()


# Convenience: create a default 3-tier cache
def create_default_cache(
    memory_size: int = 10000,
    redis_url: Optional[str] = None,
    disk_path: Optional[str] = None,
) -> CacheManager:
    """
    Build a 3-tier cache: Memory → Redis → Disk.
    Memory is always included (primary). Redis and disk are optional.
    """
    config = CacheConfig(
        max_size=memory_size,
        disk_path=disk_path,
        redis_url=redis_url,
    )
    
    tiers = [MemoryLRUBackend(config)]
    
    if redis_url:
        tiers.append(RedisClusterBackend(config))
    
    if disk_path:
        tiers.append(DiskCacheBackend(config))
    
    composite = CompositeCache(tiers, config)
    manager = CacheManager(composite)
    manager.config = config
    
    return manager


# Global singleton
_global_cache: Optional[CacheManager] = None

def get_cache() -> CacheManager:
    global _global_cache
    if _global_cache is None:
        _global_cache = create_default_cache()
    return _global_cache


__all__ = [
    "CacheConfig",
    "CacheBackend",
    "MemoryLRUBackend",
    "RedisClusterBackend",
    "DiskCacheBackend",
    "CompositeCache",
    "CacheManager",
    "create_default_cache",
    "get_cache",
]

"""
Test Suite — Caching (core_engine/cache/manager.py)
Covers: CacheConfig, MemoryLRUBackend, DiskCacheBackend, RedisClusterBackend (mocked),
       CompositeCache, CacheManager, create_default_cache.
"""
import asyncio
import pickle
import time
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core_engine.cache.manager import (
    CacheConfig,
    CacheBackend,
    MemoryLRUBackend,
    DiskCacheBackend,
    RedisClusterBackend,
    CompositeCache,
    CacheManager,
    create_default_cache,
)


# ============================================================================
# CacheConfig tests
# ============================================================================

def test_cache_config_defaults():
    cfg = CacheConfig()
    assert cfg.max_size == 10000
    assert cfg.default_ttl_seconds == 3600
    assert cfg.enable_metrics is True
    assert cfg.disk_path is None
    assert cfg.redis_url is None
    assert cfg.redis_prefix == "hdc:"

def test_cache_config_custom():
    cfg = CacheConfig(max_size=100, redis_url="redis://localhost")
    assert cfg.max_size == 100
    assert cfg.redis_url == "redis://localhost"


# ============================================================================
# MemoryLRUBackend tests
# ============================================================================

@pytest.fixture
def memory_backend():
    cfg = CacheConfig(max_size=3, default_ttl_seconds=None)
    return MemoryLRUBackend(cfg)

@pytest.mark.asyncio
async def test_memory_set_get(memory_backend):
    await memory_backend.set("k1", "v1")
    val = await memory_backend.get("k1")
    assert val == "v1"
    assert memory_backend._hits == 1
    assert memory_backend._sets == 1

@pytest.mark.asyncio
async def test_memory_get_miss(memory_backend):
    val = await memory_backend.get("missing")
    assert val is None
    assert memory_backend._misses == 1

@pytest.mark.asyncio
async def test_memory_ttl_expiration():
    cfg = CacheConfig(max_size=10, default_ttl_seconds=None)
    backend = MemoryLRUBackend(cfg)
    # Set with explicit TTL
    await backend.set("k1", "v1", ttl_seconds=0.01)
    assert await backend.get("k1") == "v1"
    await asyncio.sleep(0.02)
    assert await backend.get("k1") is None
    assert backend._misses >= 1

@pytest.mark.asyncio
async def test_memory_lru_eviction():
    cfg = CacheConfig(max_size=2, default_ttl_seconds=None)
    backend = MemoryLRUBackend(cfg)
    await backend.set("a", 1)
    await backend.set("b", 2)
    # Access 'a' to make 'b' more recent? Actually LRU: when we set 'c', oldest should be evicted.
    # Currently order: a then b. b is most recent.
    await backend.set("c", 3)  # should evict 'a' (LRU)
    assert await backend.get("a") is None  # evicted
    assert await backend.get("b") == 2
    assert await backend.get("c") == 3
    assert backend._evictions == 1

@pytest.mark.asyncio
async def test_memory_delete(memory_backend):
    await memory_backend.set("k1", "v1")
    assert await memory_backend.delete("k1") is True
    assert await memory_backend.get("k1") is None
    assert await memory_backend.delete("k2") is False

@pytest.mark.asyncio
async def test_memory_exists(memory_backend):
    await memory_backend.set("k1", "v1")
    assert await memory_backend.exists("k1") is True
    assert await memory_backend.exists("k2") is False

@pytest.mark.asyncio
async def test_memory_clear(memory_backend):
    await memory_backend.set("a", 1)
    await memory_backend.set("b", 2)
    count = await memory_backend.clear()
    assert count == 2
    assert await memory_backend.get("a") is None

@pytest.mark.asyncio
async def test_memory_stats(memory_backend):
    await memory_backend.set("k1", "v1")
    await memory_backend.get("k1")  # hit
    await memory_backend.get("missing")  # miss
    stats = await memory_backend.stats()
    assert stats["backend"] == "memory-lru"
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["sets"] == 1
    assert stats["hit_rate"] == 0.5
    assert stats["size"] == 1

def test_memory_purge_expired():
    cfg = CacheConfig(max_size=10, default_ttl_seconds=0.01)
    backend = MemoryLRUBackend(cfg)
    # We'll test internal method indirectly
    # Set some items with expiry in past manually
    now = time.time()
    old_time = now - 100
    backend._store["exp1"] = ("val1", old_time)
    backend._store["exp2"] = ("val2", None)  # no expiry
    backend._purge_expired()
    assert "exp1" not in backend._store
    assert "exp2" in backend._store


# ============================================================================
# DiskCacheBackend tests
# ============================================================================

@pytest.fixture
def disk_backend(tmp_path):
    cfg = CacheConfig(disk_path=str(tmp_path), default_ttl_seconds=None)
    return DiskCacheBackend(cfg)

@pytest.mark.asyncio
async def test_disk_set_get(disk_backend):
    await disk_backend.set("k1", {"x": 1})
    val = await disk_backend.get("k1")
    assert val == {"x": 1}

@pytest.mark.asyncio
async def test_disk_ttl_expiration(tmp_path):
    cfg = CacheConfig(disk_path=str(tmp_path), default_ttl_seconds=0.01)
    backend = DiskCacheBackend(cfg)
    await backend.set("k1", "v1")
    await asyncio.sleep(0.02)
    assert await backend.get("k1") is None

@pytest.mark.asyncio
async def test_disk_delete(disk_backend):
    await disk_backend.set("k1", "v1")
    assert await disk_backend.delete("k1") is True
    assert await disk_backend.get("k1") is None
    assert await disk_backend.delete("k2") is False

@pytest.mark.asyncio
async def test_disk_exists(disk_backend):
    await disk_backend.set("k1", "v1")
    assert await disk_backend.exists("k1") is True
    assert await disk_backend.exists("k2") is False

@pytest.mark.asyncio
async def test_disk_clear(disk_backend):
    await disk_backend.set("a", 1)
    await disk_backend.set("b", 2)
    count = await disk_backend.clear()
    assert count == 2
    # Files should be gone
    files = list(disk_backend.cache_dir.glob("*.pickle"))
    assert len(files) == 0

@pytest.mark.asyncio
async def test_disk_stats(disk_backend):
    await disk_backend.set("k1", "v1")
    stats = await disk_backend.stats()
    assert stats["backend"] == "disk"
    assert stats["files"] == 1
    assert stats["hits"] >= 0


# ============================================================================
# RedisClusterBackend tests (mocked where needed)
# ============================================================================

@pytest.fixture
def redis_backend():
    cfg = CacheConfig(redis_url="redis://localhost:6379")
    return RedisClusterBackend(cfg)

# Since redis-py is an optional dependency, we test basic behavior without client.
@pytest.mark.asyncio
async def test_redis_without_client(redis_backend):
    assert await redis_backend.get("any") is None
    assert await redis_backend.set("k","v") is False
    assert await redis_backend.delete("k") is False
    assert await redis_backend.exists("k") is False
    assert await redis_backend.clear() == 0
    stats = await redis_backend.stats()
    assert stats["connected"] is False

# We could add more tests with mocked redis client in the future if needed.


# ============================================================================
# CompositeCache tests
# ============================================================================

@pytest.fixture
def composite_cache():
    mem1 = MemoryLRUBackend(CacheConfig(max_size=2))
    mem2 = MemoryLRUBackend(CacheConfig(max_size=2))  # simulate slower tier
    return CompositeCache(tiers=[mem1, mem2], config=CacheConfig())

@pytest.mark.asyncio
async def test_composite_get_promotion(composite_cache):
    mem1, mem2 = composite_cache.tiers
    # Seed lower tier (mem2) with key
    await mem2.set("k1", "value1")
    # Get from composite should find in mem2, promote to mem1
    val = await composite_cache.get("k1")
    assert val == "value1"
    # mem1 should now have the key
    assert await mem1.get("k1") == "value1"
    # Stats: hit count increased
    assert composite_cache._hits == 1

@pytest.mark.asyncio
async def test_composite_set_writes_all_tiers(composite_cache):
    mem1, mem2 = composite_cache.tiers
    await composite_cache.set("k2", "value2")
    # Both tiers should have it
    assert await mem1.get("k2") == "value2"
    assert await mem2.get("k2") == "value2"
    assert composite_cache._sets == 1

@pytest.mark.asyncio
async def test_composite_miss(composite_cache):
    val = await composite_cache.get("nonexistent")
    assert val is None
    assert composite_cache._misses == 1

@pytest.mark.asyncio
async def test_composite_delete(composite_cache):
    mem1, mem2 = composite_cache.tiers
    await mem1.set("k", "v")
    await mem2.set("k", "v")
    result = await composite_cache.delete("k")
    assert result is True
    # Should be removed from both
    assert await mem1.get("k") is None
    assert await mem2.get("k") is None

@pytest.mark.asyncio
async def test_composite_clear(composite_cache):
    mem1, mem2 = composite_cache.tiers
    await mem1.set("a", 1)
    await mem2.set("b", 2)
    total = await composite_cache.clear()
    assert total >= 0  # sum of cleared from each
    assert await mem1.get("a") is None
    assert await mem2.get("b") is None

@pytest.mark.asyncio
async def test_composite_stats(composite_cache):
    await composite_cache.set("x", 1)
    stats = await composite_cache.stats()
    assert stats["backend"] == "composite"
    assert stats["levels"] == 2
    assert "tiers" in stats
    assert len(stats["tiers"]) == 2


# ============================================================================
# CacheManager tests (namespace, get_or_load, warmer, events)
# ============================================================================

@pytest.fixture
def simple_backend():
    return MemoryLRUBackend(CacheConfig())

@pytest.fixture
def cache_manager(simple_backend):
    return CacheManager(simple_backend)

@pytest.mark.asyncio
async def test_cache_manager_get_set(cache_manager):
    # Set uses namespace internally
    await cache_manager.set("ns1", "key1", "value1")
    val = await cache_manager.get("ns1", "key1")
    assert val == "value1"

@pytest.mark.asyncio
async def test_cache_manager_get_or_load(cache_manager):
    calls = []
    async def loader():
        calls.append(1)
        return "loaded"
    # First call: miss, loader called, value cached
    val = await cache_manager.get_or_load("ns", "k", loader)
    assert val == "loaded"
    assert len(calls) == 1
    # Second call: hit from cache, loader not called
    val2 = await cache_manager.get_or_load("ns", "k", loader)
    assert val2 == "loaded"
    assert len(calls) == 1

@pytest.mark.asyncio
async def test_cache_manager_warmer(cache_manager):
    warmer_called = False
    async def warmer():
        nonlocal warmer_called
        warmer_called = True
        return {"k1": "warmed"}
    cache_manager.register_warmer("ns1", warmer)
    count = await cache_manager.warm_namespace("ns1")
    assert count == 1
    assert warmer_called is True
    # Verify key available
    assert await cache_manager.get("ns1", "k1") == "warmed"

@pytest.mark.asyncio
async def test_cache_manager_events(cache_manager):
    events = []
    def handler(namespace, key, value):
        events.append((namespace, key, value))
    cache_manager.on_event("set", "ns1", handler)
    await cache_manager.set("ns1", "k1", "v1")
    assert events == [("ns1", "k1", "v1")]

@pytest.mark.asyncio
async def test_cache_manager_delete_emits_event(cache_manager):
    events = []
    cache_manager.on_event("delete", "ns1", lambda ns, k, v: events.append((ns, k)))
    await cache_manager.set("ns1", "k1", "v1")
    await cache_manager.delete("ns1", "k1")
    assert ("ns1", "k1") in events

@pytest.mark.asyncio
async def test_cache_manager_stats(cache_manager):
    await cache_manager.set("ns", "k", 1)
    stats = await cache_manager.stats()
    # Should delegate to backend.stats
    assert "backend" in stats


# ============================================================================
# create_default_cache tests
# ============================================================================

def test_create_default_cache_memory_only():
    manager = create_default_cache(memory_size=100)
    assert manager is not None
    # Should have composite with 1 tier
    assert isinstance(manager.backend, CompositeCache)
    assert len(manager.backend.tiers) == 1
    assert isinstance(manager.backend.tiers[0], MemoryLRUBackend)

def test_create_default_cache_with_disk(tmp_path):
    manager = create_default_cache(memory_size=100, disk_path=str(tmp_path))
    tiers = manager.backend.tiers
    # Should have Memory and Disk
    assert len(tiers) == 2
    assert isinstance(tiers[0], MemoryLRUBackend)
    assert isinstance(tiers[1], DiskCacheBackend)

def test_create_default_cache_all_tiers(monkeypatch, tmp_path):
    # Simulate redis available
    class FakeRedis:
        pass
    # We'll patch RedisClusterBackend initialization to not require real redis
    monkeypatch.setattr("core_engine.cache.manager.RedisClusterBackend", MagicMock())
    manager = create_default_cache(memory_size=100, redis_url="redis://localhost", disk_path=str(tmp_path))
    tiers = manager.backend.tiers
    # Should have 3 tiers
    assert len(tiers) == 3
    assert isinstance(tiers[1], MagicMock)  # mocked

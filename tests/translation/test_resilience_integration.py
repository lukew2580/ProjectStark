"""
Integration tests — Translation Resilience (registry + backends)
Covers: cache integration, circuit breaker trip, bulkhead rejection, in-flight dedup.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from core_engine.translation.registry import TranslationRegistry, BackendType, TranslationResult
from core_engine.translation.backends.libretranslate import LibreTranslateBackend
from core_engine.translation.backends.mtranserver import MTranServerBackend
from core_engine.cache.manager import MemoryLRUBackend, CacheConfig, CacheManager
from core_engine.resilience import CircuitState, get_circuit_breaker, get_bulkhead


# ============================================================================
# Test fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def clear_global_state():
    """Clear all global registries before each test."""
    # Clear resilience globals
    from core_engine.resilience import _global_breakers, _global_bulkheads, _global_fallbacks
    _global_breakers.clear()
    _global_bulkheads.clear()
    _global_fallbacks.clear()
    # Clear translation registry global
    from core_engine.translation.registry import _global_registry
    global _global_registry
    _global_registry = None
    yield
    # No teardown needed


@pytest.fixture
def cache_manager():
    """Simple in-memory cache for testing."""
    backend = MemoryLRUBackend(CacheConfig(max_size=100))
    return CacheManager(backend)


@pytest.fixture
def registry_with_mock_backends(cache_manager):
    """
    Registry with cache + bulkhead(3) + mock backends.
    Returns (registry, mock_lt, mock_mt).
    """
    # Global state cleared by autouse fixture
    registry = TranslationRegistry(cache_manager=cache_manager, bulkhead_max=3)

    # Create registry with small bulkhead for rejection testing
    registry = TranslationRegistry(cache_manager=cache_manager, bulkhead_max=3)

    # Create mock backends
    mock_lt = AsyncMock(spec=LibreTranslateBackend)
    mock_lt.translate = AsyncMock(return_value=TranslationResult(
        text="Hola", source_lang="en", target_lang="es", backend="libretranslate", confidence=0.9
    ))
    mock_lt.translate_raw = AsyncMock(return_value=TranslationResult(
        text="Hola", source_lang="en", target_lang="es", backend="libretranslate", confidence=0.9
    ))

    mock_mt = AsyncMock(spec=MTranServerBackend)
    mock_mt.translate = AsyncMock(return_value=TranslationResult(
        text="Hola", source_lang="en", target_lang="es", backend="mtranserver", confidence=0.95
    ))
    mock_mt.translate_raw = AsyncMock(return_value=TranslationResult(
        text="Hola", source_lang="en", target_lang="es", backend="mtranserver", confidence=0.95
    ))

    # Register backends in priority order
    registry.register_backend(BackendType.MTRANSERVER, mock_mt)  # priority 1 (default)
    registry.register_backend(BackendType.LIBRETRANSLATE, mock_lt)  # priority 2 (default)

    return registry, mock_lt, mock_mt


@pytest.fixture
def failing_mock_backend():
    """Backend that raises exceptions (for circuit breaker tests)."""
    mock = AsyncMock(spec=LibreTranslateBackend)
    mock.translate = AsyncMock(side_effect=RuntimeError("Backend failure"))
    mock.translate_raw = AsyncMock(side_effect=RuntimeError("Backend failure"))
    return mock


# ============================================================================
# 1. Cache integration tests
# ============================================================================

@pytest.mark.asyncio
async def test_cache_hit_prevents_backend_call(cache_manager, registry_with_mock_backends):
    """Cache hit should return cached value without invoking any backend."""
    registry, mock_lt, mock_mt = registry_with_mock_backends

    # First call — cache miss — backends invoked
    result1 = await registry.translate("Hello", "en", "es")
    assert result1.text == "Hola"
    assert mock_mt.translate.call_count == 1  # primary backend called
    assert mock_lt.translate.call_count == 0  # fallback not called

    # Second call — cache hit — no backend calls
    result2 = await registry.translate("Hello", "en", "es")
    assert result2.text == "Hola"
    assert mock_mt.translate.call_count == 1  # unchanged
    assert mock_lt.translate.call_count == 0  # unchanged
    assert result1.text == result2.text


@pytest.mark.asyncio
async def test_cache_miss_calls_backends(cache_manager, registry_with_mock_backends):
    """Cache miss should call backends and store successful result."""
    registry, mock_lt, mock_mt = registry_with_mock_backends

    # Different text — cache miss
    result = await registry.translate("Goodbye", "en", "fr")
    assert result.text == "Hola"
    assert mock_mt.translate.call_count == 1

    # Verify it's now cached (check backend directly with stringified key)
    cached = await cache_manager.backend.get(str(("Goodbye", "en", "fr")))
    assert cached is not None
    assert cached.text == "Hola"


@pytest.mark.asyncio
async def test_cache_disabled_when_no_cache_manager():
    """Registry without cache manager should still function."""
    from core_engine.translation.registry import _global_registry
    global _global_registry
    _global_registry = None
    # Global state cleared by autouse fixture

    registry = TranslationRegistry(cache_manager=None, bulkhead_max=5)
    mock_lt = AsyncMock(spec=LibreTranslateBackend)
    mock_lt.translate = AsyncMock(return_value=TranslationResult(
        text="Hola", source_lang="en", target_lang="es", backend="libretranslate", confidence=0.9
    ))
    registry.register_backend(BackendType.LIBRETRANSLATE, mock_lt)

    result = await registry.translate("Hello", "en", "es")
    assert result.text == "Hola"
    assert mock_lt.translate.call_count == 1


# ============================================================================
# 2. Circuit breaker integration tests
# ============================================================================

class CircuitBreakingTestBackend:
    """
    Test backend with real CircuitBreakerMiddleware.
    Used to verify registry behavior when a backend's circuit trips.
    """
    def __init__(self, failure_threshold: int = 3):
        from core_engine.resilience import CircuitBreakerMiddleware, CircuitBreakerConfig
        self._raw_call_count = 0
        self._breaker_middleware = CircuitBreakerMiddleware(
            "test-circuit",
            CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                recovery_timeout_seconds=1.0,
                slow_call_threshold_seconds=10.0
            )
        )
        self._translate_guarded = self._breaker_middleware(self._translate_raw)

    async def translate(self, text, source_lang="auto", target_lang="en"):
        return await self._translate_guarded(text, source_lang, target_lang)

    async def _translate_raw(self, text, source_lang, target_lang):
        self._raw_call_count += 1
        raise RuntimeError("Simulated backend failure")

    @property
    def raw_call_count(self):
        return self._raw_call_count

    @property
    def breaker(self):
        return self._breaker_middleware.breaker


@pytest.mark.asyncio
async def test_circuit_breaker_trips_after_threshold(cache_manager):
    """
    Circuit breaker should trip after consecutive failures, preventing further backend calls.
    Registry should then fall back to the next backend.
    """
    # Primary backend that will trip
    primary = CircuitBreakingTestBackend(failure_threshold=3)

    # Fallback backend that always works
    fallback = AsyncMock(spec=MTranServerBackend)
    fallback.translate = AsyncMock(return_value=TranslationResult(
        text="Fallback", source_lang="en", target_lang="es", backend="mtranserver", confidence=0.95
    ))

    registry = TranslationRegistry(cache_manager=None, bulkhead_max=5)
    registry._init_configs = lambda: None
    registry.configs = {
        BackendType.MTRANSERVER: type('cfg', (), {'enabled': True, 'priority': 1})(),
        BackendType.LIBRETRANSLATE: type('cfg', (), {'enabled': True, 'priority': 2})(),
    }
    registry.register_backend(BackendType.MTRANSERVER, primary)
    registry.register_backend(BackendType.LIBRETRANSLATE, fallback)

    # Failures 1-3: primary fails, fallback handles
    for i in range(3):
        result = await registry.translate("test", "en", "es")
        assert result.text == "Fallback"
        assert primary.raw_call_count == i + 1
        assert fallback.translate.call_count == i + 1

    assert primary.breaker.state == CircuitState.OPEN

    # 4th call: primary circuit is OPEN → should NOT call _translate_raw (raw_call_count unchanged)
    # Registry catches the circuit breaker exception and tries fallback
    result = await registry.translate("test4", "en", "es")
    assert result.text == "Fallback"
    assert primary.raw_call_count == 3  # no new raw call
    assert fallback.translate.call_count == 4


@pytest.mark.asyncio
async def test_circuit_breaker_allows_fallback_to_next_backend(cache_manager):
    """
    When a backend's circuit breaker trips, the registry should automatically
    fall back to the next backend without raising an error to the caller.
    """
    # Primary backend that fails 3 times then continues raising "circuit open" (simulates tripped state)
    primary = CircuitBreakingTestBackend(failure_threshold=3)

    # Fallback backend that always works
    fallback = AsyncMock(spec=MTranServerBackend)
    fallback.translate = AsyncMock(return_value=TranslationResult(
        text="Fallback", source_lang="en", target_lang="es", backend="mtranserver", confidence=0.95
    ))

    registry = TranslationRegistry(cache_manager=None, bulkhead_max=5)
    registry._init_configs = lambda: None
    registry.configs = {
        BackendType.LIBRETRANSLATE: type('cfg', (), {'enabled': True, 'priority': 1})(),
        BackendType.MTRANSERVER: type('cfg', (), {'enabled': True, 'priority': 2})(),
    }
    registry.register_backend(BackendType.LIBRETRANSLATE, primary)
    registry.register_backend(BackendType.MTRANSERVER, fallback)

    # First 3 calls: primary fails consecutively, trip circuit, fallback handles
    for i in range(3):
        result = await registry.translate("test", "en", "es")
        assert result.text == "Fallback"
        assert primary.raw_call_count == i + 1
        assert fallback.translate.call_count == i + 1

    assert primary.breaker.state == CircuitState.OPEN

    # Subsequent call: primary is OPEN → immediately raises circuit open exception (no raw call)
    # Registry catches and tries fallback
    result = await registry.translate("later", "en", "es")
    assert result.text == "Fallback"
    assert primary.raw_call_count == 3  # unchanged
    assert fallback.translate.call_count == 4
    assert fallback.translate.call_count == 4


# ============================================================================
# 3. Bulkhead rejection tests
# ============================================================================

@pytest.mark.asyncio
async def test_bulkhead_rejects_when_full(cache_manager, registry_with_mock_backends):
    """
    When bulkhead is full (max_concurrent acquired) and max_queue_size=0,
    additional translate calls should be rejected immediately without invoking any backend.
    """
    registry, mock_lt, mock_mt = registry_with_mock_backends

    # Controlled backend: will hold bulkhead slot until explicitly released
    started = asyncio.Event()
    block_event = asyncio.Event()

    async def holding_backend(text, source_lang, target_lang):
        # Signal that we've started (after acquiring bulkhead)
        started.set()
        # Wait for release signal before completing
        await block_event.wait()
        return await mock_mt.translate(text, source_lang, target_lang)

    original_translate = mock_mt.translate
    mock_mt.translate = holding_backend

    # Start 3 tasks; each will acquire bulkhead and then block
    t1 = asyncio.create_task(registry.translate("t1", "en", "es"))
    t2 = asyncio.create_task(registry.translate("t2", "en", "es"))
    t3 = asyncio.create_task(registry.translate("t3", "en", "es"))

    # Wait until all three have acquired bulkhead
    # Check bulkhead stats for current count
    for _ in range(100):  # up to 1.0 sec
        if registry._bulkhead.stats()["current"] == 3:
            break
        await asyncio.sleep(0.01)
    else:
        pytest.fail("Bulkhead slots not filled by tasks")

    # Fourth call should be rejected immediately
    with pytest.raises(RuntimeError, match="Translation bulkhead full"):
        await registry.translate("t4", "en", "es")

    # Release the three holding tasks
    block_event.set()
    results = await asyncio.gather(t1, t2, t3, return_exceptions=True)
    assert len(results) == 3
    for r in results:
        assert isinstance(r, TranslationResult)

    # After releasing, bulkhead slots free, new call should succeed
    result = await registry.translate("t5", "en", "es")
    assert isinstance(result, TranslationResult)

    # Cleanup
    mock_mt.translate = original_translate
# 4. In-flight deduplication tests
# ============================================================================

@pytest.mark.asyncio
async def test_in_flight_deduplication(cache_manager, registry_with_mock_backends):
    """Concurrent translate() calls for the same text should only invoke backend once."""
    registry, mock_lt, mock_mt = registry_with_mock_backends

    # Mock backend to track how many times it's actually called
    call_count = 0
    original_translate = mock_mt.translate

    async def counting_translate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)  # Simulate network latency
        return await original_translate(*args, **kwargs)

    mock_mt.translate = counting_translate

    # Fire 10 concurrent translations for the same text
    tasks = [registry.translate("duplicate", "en", "es") for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # All should return same result
    assert all(r.text == "Hola" for r in results)
    assert len(set(id(r) for r in results)) == 1  # same object (cached after first)

    # Backend should have been called exactly once
    assert call_count == 1, f"Backend called {call_count} times, expected 1"


@pytest.mark.asyncio
async def test_in_flight_deduplication_different_texts(cache_manager, registry_with_mock_backends):
    """Different texts should each trigger separate backend calls."""
    registry, mock_lt, mock_mt = registry_with_mock_backends

    call_count = 0
    original_translate = mock_mt.translate

    async def counting_translate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return await original_translate(*args, **kwargs)

    mock_mt.translate = counting_translate

    # Different texts concurrently
    tasks = [
        registry.translate("text1", "en", "es"),
        registry.translate("text2", "en", "es"),
        registry.translate("text3", "en", "es"),
    ]
    await asyncio.gather(*tasks)

    # Each distinct text should invoke backend once
    assert call_count == 3


# ============================================================================
# 5. Combined scenario: cache + circuit breaker + dedup
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_resilience_flow(cache_manager):
    """Full scenario: cache miss → backend success → cached; dedup works."""
    backend_call_count = 0

    async def mock_translate(text, source_lang, target_lang):
        nonlocal backend_call_count
        backend_call_count += 1
        await asyncio.sleep(0.05)
        return TranslationResult(
            text=f"trans({text})",
            source_lang=source_lang,
            target_lang=target_lang,
            backend="mtranserver",
            confidence=0.95
        )

    mock_mt = AsyncMock(spec=MTranServerBackend)
    mock_mt.translate = AsyncMock(side_effect=mock_translate)

    registry = TranslationRegistry(cache_manager=cache_manager, bulkhead_max=5)
    registry.register_backend(BackendType.MTRANSERVER, mock_mt)

    # 1️⃣ First call — cache miss
    r1 = await registry.translate("hello", "en", "es")
    assert r1.text == "trans(hello)"
    assert backend_call_count == 1

    # 2️⃣ Concurrent duplicate — should dedup
    tasks = [registry.translate("hello", "en", "es") for _ in range(5)]
    results = await asyncio.gather(*tasks)
    assert all(r.text == "trans(hello)" for r in results)
    assert backend_call_count == 1  # still just 1 call!

    # 3️⃣ Second call after cache warm — cache hit
    r2 = await registry.translate("hello", "en", "es")
    assert r2.text == "trans(hello)"
    assert backend_call_count == 1  # no new call

    # 4️⃣ New text — cache miss, new backend call
    r3 = await registry.translate("world", "en", "es")
    assert r3.text == "trans(world)"
    assert backend_call_count == 2

    # Verify cache contents via backend
    cached = await cache_manager.backend.get(str(("hello", "en", "es")))
    assert cached is not None
    assert cached.text == "trans(hello)"


# ============================================================================
# 6. Bulkhead + fallback interaction
# ============================================================================

@pytest.mark.asyncio
async def test_bulkhead_rejection_triggers_fallback(cache_manager):
    """
    When bulkhead is full and a backend is busy, the registry raises
    RuntimeError("Translation bulkhead full"). Caller (or higher-level
    logic) can catch this and try alternative backends. This test verifies
    that the rejection occurs promptly.
    """
    # Primary slow backend
    async def slow_backend_func(text, source_lang, target_lang):
        await asyncio.sleep(0.2)
        return TranslationResult(text="slow", source_lang=source_lang, target_lang=target_lang, backend="slow", confidence=0.9)

    slow_mock = AsyncMock(spec=MTranServerBackend)
    slow_mock.translate = AsyncMock(side_effect=slow_backend_func)

    # Fast fallback backend
    fast_mock = AsyncMock(spec=LibreTranslateBackend)
@pytest.mark.asyncio
async def test_bulkhead_rejection_triggers_fallback(cache_manager):
    """
    When bulkhead is full and a backend is busy, additional translate calls
    are rejected immediately. This test verifies that rejection and that after
    freeing slots, subsequent calls proceed to the primary backend.
    """
    # Primary slow backend that holds until released
    block_event = asyncio.Event()

    async def holding_backend(text, source_lang, target_lang):
        await block_event.wait()  # hold bulkhead slot
        return TranslationResult(text="slow", source_lang=source_lang, target_lang=target_lang, backend="slow", confidence=0.9)

    slow_mock = AsyncMock(spec=MTranServerBackend)
    slow_mock.translate = AsyncMock(side_effect=holding_backend)

    fast_mock = AsyncMock(spec=LibreTranslateBackend)  # fallback (not used here)

    registry = TranslationRegistry(cache_manager=None, bulkhead_max=2)
    registry._init_configs = lambda: None
    registry.configs = {
        BackendType.MTRANSERVER: type('cfg', (), {'enabled': True, 'priority': 1})(),
        BackendType.LIBRETRANSLATE: type('cfg', (), {'enabled': True, 'priority': 2})(),
    }
    registry.register_backend(BackendType.MTRANSERVER, slow_mock)
    registry.register_backend(BackendType.LIBRETRANSLATE, fast_mock)

    # Occupy both bulkhead slots
    t1 = asyncio.create_task(registry.translate("t1", "en", "es"))
    t2 = asyncio.create_task(registry.translate("t2", "en", "es"))

    # Wait until bulkhead is full
    for _ in range(100):
        if registry._bulkhead.stats()["current"] == 2:
            break
        await asyncio.sleep(0.01)
    else:
        pytest.fail("Bulkhead not full")

    # Third call should be rejected immediately
    with pytest.raises(RuntimeError, match="Translation bulkhead full"):
        await registry.translate("t3", "en", "es")

    # Release the holding tasks
    block_event.set()
    results = await asyncio.gather(t1, t2, return_exceptions=True)
    assert len(results) == 2
    for r in results:
        assert isinstance(r, TranslationResult)
        assert r.text == "slow"

    # After release, new call goes to slow_mock (which now returns quickly)
    result = await registry.translate("t4", "en", "es")
    assert result.text == "slow"


# ============================================================================
# 7. Cache key correctness
# ============================================================================

@pytest.mark.asyncio
async def test_cache_key_includes_all_translation_params(cache_manager):
    """Cache key must include text, source_lang, AND target_lang."""
    call_count = 0
    mock_mt = AsyncMock()

    async def counting_translate(text, source_lang, target_lang):
        nonlocal call_count
        call_count += 1
        return TranslationResult(
            text=f"{text}:{source_lang}→{target_lang}",
            source_lang=source_lang,
            target_lang=target_lang,
            backend="mtranserver",
            confidence=0.9
        )

    mock_mt.translate = AsyncMock(side_effect=counting_translate)

    registry = TranslationRegistry(cache_manager=cache_manager, bulkhead_max=5)
    registry.register_backend(BackendType.MTRANSERVER, mock_mt)

    # Same text, different target → separate cache entries
    r1 = await registry.translate("hello", "en", "es")
    r2 = await registry.translate("hello", "en", "fr")
    r3 = await registry.translate("hello", "en", "es")  # repeat of r1

    assert call_count == 2  # es and fr each called once; 3rd call cached
    assert r1.text == "hello:en→es"
    assert r2.text == "hello:en→fr"
    assert r3.text == "hello:en→es"

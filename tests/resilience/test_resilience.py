"""
Test Suite — Resilience Patterns (core_engine/resilience/)
Covers: CircuitBreaker, CircuitBreakerMiddleware, FallbackChain, Bulkhead,
        TimeoutCascade, global registries, create_guarded_backend.
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core_engine.resilience import (
    CircuitState,
    CircuitBreakerConfig,
    CircuitBreaker,
    CircuitBreakerMiddleware,
    FallbackChain,
    Bulkhead,
    TimeoutCascade,
    get_circuit_breaker,
    get_bulkhead,
    register_circuit_breaker,
    register_bulkhead,
    register_fallback,
    create_guarded_backend,
)

# ============================================================================
# CircuitBreakerConfig tests
# ============================================================================

def test_config_defaults():
    cfg = CircuitBreakerConfig()
    assert cfg.failure_threshold == 5
    assert cfg.recovery_timeout_seconds == 30.0
    assert cfg.expected_exception == (Exception,)
    assert cfg.window_size == 100
    assert cfg.minimum_calls == 10
    assert cfg.slow_call_threshold_seconds == 5.0
    assert cfg.on_state_change is None

def test_config_custom():
    def callback(name, old, new):
        pass
    cfg = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout_seconds=10.0,
        expected_exception=(ValueError, TypeError),
        window_size=50,
        minimum_calls=5,
        slow_call_threshold_seconds=2.0,
        on_state_change=callback,
    )
    assert cfg.failure_threshold == 3
    assert cfg.recovery_timeout_seconds == 10.0
    assert cfg.expected_exception == (ValueError, TypeError)
    assert cfg.window_size == 50
    assert cfg.minimum_calls == 5
    assert cfg.slow_call_threshold_seconds == 2.0
    assert cfg.on_state_change is callback


# ============================================================================
# CircuitBreaker tests
# ============================================================================

@pytest.fixture
def circuit_breaker():
    return CircuitBreaker("test-breaker")

@pytest.fixture
def circuit_breaker_with_callback():
    events = []
    def callback(name, old, new):
        events.append((old, new))
    cfg = CircuitBreakerConfig(on_state_change=callback)
    return CircuitBreaker("test-breaker", cfg), events

def test_circuit_breaker_initial_state(circuit_breaker):
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.name == "test-breaker"
    assert circuit_breaker._consecutive_failures == 0
    assert circuit_breaker._total_calls == 0

def test_record_success_closed(circuit_breaker):
    circuit_breaker.record_success()
    assert circuit_breaker._consecutive_failures == 0
    assert circuit_breaker._recent_calls[-1] is True
    assert circuit_breaker._total_calls == 1
    assert circuit_breaker.state == CircuitState.CLOSED

def test_record_success_half_open_transitions_to_closed(circuit_breaker_with_callback):
    breaker, events = circuit_breaker_with_callback
    breaker.state = CircuitState.HALF_OPEN
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert len(events) == 1
    assert events[0] == (CircuitState.HALF_OPEN, CircuitState.CLOSED)

def test_record_failure_increments_consecutive(circuit_breaker):
    circuit_breaker.record_failure()
    assert circuit_breaker._consecutive_failures == 1
    assert circuit_breaker._total_calls == 1
    assert circuit_breaker._total_failures == 1
    assert circuit_breaker._recent_calls[-1] is False

def test_record_failure_trips_open(circuit_breaker):
    cfg = CircuitBreakerConfig(failure_threshold=3)
    breaker = CircuitBreaker("test", cfg)
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED
    breaker.record_failure()  # 3rd failure trips
    assert breaker.state == CircuitState.OPEN
    assert breaker._last_failure_time is not None

def test_record_timeout_aliases_to_failure(circuit_breaker):
    circuit_breaker.record_timeout()
    assert circuit_breaker._consecutive_failures == 1
    assert circuit_breaker._total_failures == 1

def test_record_slow_call_counts_when_exceeded(circuit_breaker):
    cfg = CircuitBreakerConfig(slow_call_threshold_seconds=1.0)
    breaker = CircuitBreaker("test", cfg)
    breaker.record_slow_call(0.5)
    assert breaker._total_slow_calls == 0
    breaker.record_slow_call(2.0)
    assert breaker._total_slow_calls == 1

def test_can_execute_closed_returns_true(circuit_breaker):
    assert circuit_breaker.can_execute() is True

def test_can_execute_open_returns_false_until_recovery(circuit_breaker_with_callback):
    breaker, _ = circuit_breaker_with_callback
    cfg = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_seconds=0.1)
    breaker2 = CircuitBreaker("test2", cfg)
    breaker2.record_failure()  # trip to OPEN
    assert breaker2.state == CircuitState.OPEN
    assert breaker2.can_execute() is False
    time.sleep(0.15)
    # Next can_execute() call checks timeout and transitions to HALF_OPEN
    assert breaker2.can_execute() is True
    assert breaker2.state == CircuitState.HALF_OPEN

def test_can_execute_half_open_returns_true(circuit_breaker_with_callback):
    breaker, _ = circuit_breaker_with_callback
    breaker.state = CircuitState.HALF_OPEN
    assert breaker.can_execute() is True

def test_transition_to_calls_callback(circuit_breaker_with_callback):
    breaker, events = circuit_breaker_with_callback
    breaker._transition_to(CircuitState.OPEN)
    assert breaker.state == CircuitState.OPEN
    assert len(events) == 1
    assert events[0] == (CircuitState.CLOSED, CircuitState.OPEN)

def test_transition_to_suppresses_callback_exceptions():
    events = []
    def bad_callback(name, old, new):
        events.append("called")
        raise RuntimeError("boom")
    cfg = CircuitBreakerConfig(on_state_change=bad_callback)
    breaker = CircuitBreaker("test", cfg)
    breaker._transition_to(CircuitState.OPEN)
    # Callback should have been called despite error
    assert len(events) == 1
    assert breaker.state == CircuitState.OPEN

def test_health_score_empty_calls_returns_1(circuit_breaker):
    assert circuit_breaker.health_score() == 1.0

def test_health_score_mixed_calls(circuit_breaker):
    cfg = CircuitBreakerConfig(window_size=4)
    breaker = CircuitBreaker("test", cfg)
    breaker.record_success()
    breaker.record_success()
    breaker.record_failure()
    breaker.record_failure()
    # health = 2/4 = 0.5
    assert breaker.health_score() == 0.5

def test_stats_returns_dict(circuit_breaker):
    cfg = CircuitBreakerConfig(failure_threshold=3)
    breaker = CircuitBreaker("test", cfg)
    breaker.record_success()
    breaker.record_failure()
    stats = breaker.stats()
    assert stats["name"] == "test"
    assert stats["state"] == "closed"
    assert stats["total_calls"] == 2
    assert stats["total_failures"] == 1
    assert stats["consecutive_failures"] == 1
    assert "health" in stats
    assert "recent_success_rate" in stats


# ============================================================================
# CircuitBreakerMiddleware tests
# ============================================================================

@pytest.fixture
def middleware():
    return CircuitBreakerMiddleware("test-middleware")

@pytest.mark.asyncio
async def test_middleware_allows_call_when_closed():
    breaker_mock = MagicMock(spec=CircuitBreaker)
    breaker_mock.can_execute.return_value = True
    breaker_mock.record_success = MagicMock()
    breaker_mock.record_failure = MagicMock()
    breaker_mock.config = CircuitBreakerConfig()

    class TestMiddleware(CircuitBreakerMiddleware):
        def __init__(self, name, config=None):
            self.breaker = breaker_mock
            self.config = config or CircuitBreakerConfig()

    async def fake_func():
        return "success"

    wrapped = TestMiddleware("test").__call__(fake_func)
    result = await wrapped()
    assert result == "success"
    breaker_mock.can_execute.assert_called_once()
    breaker_mock.record_success.assert_called_once()

@pytest.mark.asyncio
async def test_middleware_rejects_when_open():
    breaker_mock = MagicMock(spec=CircuitBreaker)
    breaker_mock.can_execute.return_value = False
    breaker_mock.record_failure = MagicMock()
    breaker_mock.config = CircuitBreakerConfig(expected_exception=(ValueError,))

    class TestMiddleware(CircuitBreakerMiddleware):
        def __init__(self, name, config=None):
            self.breaker = breaker_mock
            self.config = config or CircuitBreakerConfig()

    async def fake_func():
        return "should not run"

    # Fix mock to have the name attribute
    breaker_mock.name = "test-middleware"
    wrapped = TestMiddleware("test").__call__(fake_func)
    with pytest.raises(RuntimeError, match="Circuit 'test-middleware' is OPEN"):
        await wrapped()
    breaker_mock.can_execute.assert_called_once()

@pytest.mark.asyncio
async def test_middleware_records_failure_on_expected_exception():
    breaker_mock = MagicMock(spec=CircuitBreaker)
    breaker_mock.can_execute.return_value = True
    breaker_mock.record_failure = MagicMock()
    breaker_mock.config = CircuitBreakerConfig(expected_exception=(ValueError,))

    class TestMiddleware(CircuitBreakerMiddleware):
        def __init__(self, name, config=None):
            self.breaker = breaker_mock
            self.config = config or CircuitBreakerConfig()

    async def fake_func():
        raise ValueError("test error")

    wrapped = TestMiddleware("test").__call__(fake_func)
    with pytest.raises(ValueError):
        await wrapped()
    breaker_mock.record_failure.assert_called_once()
    breaker_mock.record_success.assert_not_called()

@pytest.mark.asyncio
async def test_middleware_records_timeout_on_timeout_error():
    breaker_mock = MagicMock(spec=CircuitBreaker)
    breaker_mock.can_execute.return_value = True
    breaker_mock.record_timeout = MagicMock()
    breaker_mock.config = CircuitBreakerConfig()

    class TestMiddleware(CircuitBreakerMiddleware):
        def __init__(self, name, config=None):
            self.breaker = breaker_mock
            self.config = config or CircuitBreakerConfig()

    async def fake_func():
        raise asyncio.TimeoutError("timeout")

    wrapped = TestMiddleware("test").__call__(fake_func)
    with pytest.raises(asyncio.TimeoutError):
        await wrapped()
    breaker_mock.record_timeout.assert_called_once()


# ============================================================================
# FallbackChain tests
# ============================================================================

@pytest.fixture
def fallback_chain():
    async def strategy1(x):
        return x * 2
    async def strategy2(x):
        return x * 3
    async def strategy3(x):
        return x * 4
    return FallbackChain(strategy1, strategy2, strategy3)

@pytest.mark.asyncio
async def test_fallback_chain_execute_first_succeeds(fallback_chain):
    result = await fallback_chain.execute(5)
    assert result == 10  # strategy1: 5*2
    assert fallback_chain.last_used_index() == 0

@pytest.mark.asyncio
async def test_fallback_chain_skips_on_failure():
    call_count = []
    async def failing_strategy(x):
        call_count.append(1)
        raise ValueError("fail")
    async def second_strategy(x):
        call_count.append(2)
        return x * 2

    chain = FallbackChain(failing_strategy, second_strategy)
    result = await chain.execute(5)
    assert result == 10
    assert chain.last_used_index() == 1
    assert len(call_count) == 2  # both were tried

@pytest.mark.asyncio
async def test_fallback_chain_raises_when_all_fail():
    async def always_fail(x):
        raise ValueError("fail")
    chain = FallbackChain(always_fail, always_fail)
    with pytest.raises(RuntimeError, match="All fallback strategies failed"):
        await chain.execute(5)

@pytest.mark.asyncio
async def test_fallback_chain_custom_exceptions():
    call_order = []
    async def strategy_a(x):
        call_order.append("a")
        raise KeyError("wrong key")
    async def strategy_b(x):
        call_order.append("b")
        return "b-result"

    # Only catch KeyError, not other exceptions
    chain = FallbackChain(strategy_a, strategy_b, fallback_exceptions=(KeyError,))
    result = await chain.execute(5)
    assert result == "b-result"
    assert call_order == ["a", "b"]

@pytest.mark.asyncio
async def test_fallback_chain_last_used_index_none_when_no_calls():
    chain = FallbackChain()
    # Empty chain not allowed in practice but for completeness
    with pytest.raises(RuntimeError):
        # Actually, FallbackChain with no strategies will immediately fail
        await chain.execute()

@pytest.mark.asyncio
async def test_fallback_chain_tracks_multiple_calls():
    call_log = []
    async def s1(x):
        call_log.append(("s1", x))
        return x
    async def s2(x):
        call_log.append(("s2", x))
        return x * 2

    chain = FallbackChain(s1, s2)

    result1 = await chain.execute(1)
    assert result1 == 1
    assert chain.last_used_index() == 0

    call_log.clear()
    result2 = await chain.execute(2)
    # s1 returns x directly, so result should be 2 not 4
    assert result2 == 2
    assert chain.last_used_index() == 0


# ============================================================================
# Bulkhead tests
# ============================================================================

@pytest.fixture
def bulkhead():
    return Bulkhead(max_concurrent=2)

@pytest.mark.asyncio
async def test_bulkhead_acquire_release(bulkhead):
    assert await bulkhead.acquire() is True
    assert bulkhead._current == 1
    bulkhead.release()
    assert bulkhead._current == 0

@pytest.mark.asyncio
async def test_bulkhead_max_concurrency_limit():
    """Only max_concurrent acquisitions succeed; others block until release."""
    bulkhead = Bulkhead(max_concurrent=2)
    acquired = []

    async def worker(id, bulkhead, evt):
        await bulkhead.acquire()
        acquired.append(id)
        evt.set()  # signal acquired
        await asyncio.sleep(0.05)
        bulkhead.release()

    evt1 = asyncio.Event()
    evt2 = asyncio.Event()
    evt3 = asyncio.Event()

    task1 = asyncio.create_task(worker(1, bulkhead, evt1))
    task2 = asyncio.create_task(worker(2, bulkhead, evt2))
    task3 = asyncio.create_task(worker(3, bulkhead, evt3))

    await asyncio.wait_for(asyncio.gather(evt1.wait(), evt2.wait()), timeout=1.0)
    # After 2 acquire, the 3rd should be blocked
    assert len(acquired) == 2
    assert 1 in acquired and 2 in acquired

    # Wait for releases, then 3rd should proceed
    await asyncio.wait_for(asyncio.gather(task1, task2, task3), timeout=2.0)
    assert 3 in acquired
    assert bulkhead._current == 0

@pytest.mark.asyncio
async def test_bulkhead_queue_full_rejection():
    """When queue_size=0, acquire rejects immediately when capacity full."""
    bulkhead = Bulkhead(max_concurrent=2, max_queue_size=0)
    sem = asyncio.Semaphore(0)  # Block releases to hold slots

    async def hold():
        await bulkhead.acquire()
        await sem.acquire()  # never release (hold forever)

    task1 = asyncio.create_task(hold())
    task2 = asyncio.create_task(hold())
    await asyncio.sleep(0.05)  # let both acquire

    # Both slots are occupied; new acquire should be rejected immediately
    result = await bulkhead.acquire()
    assert result is False
    assert bulkhead._rejected == 1

    # After another attempt, rejected count rises
    result2 = await bulkhead.acquire()
    assert result2 is False
    assert bulkhead._rejected == 2

    # Cleanup: allow holders to exit
    sem.release()
    sem.release()
    await task1
    await task2

@pytest.mark.asyncio
async def test_bulkhead_context_manager():
    bulkhead = Bulkhead(max_concurrent=1)
    async with bulkhead:
        assert bulkhead._current == 1
    assert bulkhead._current == 0

@pytest.mark.asyncio
async def test_bulkhead_context_manager_rejects_when_full():
    bulkhead = Bulkhead(max_concurrent=1, max_queue_size=0)
    async with bulkhead:
        # Second entry should raise because capacity full and no queue allowed
        with pytest.raises(RuntimeError, match="Bulkhead full — request rejected"):
            async with bulkhead:
                pass

def test_bulkhead_stats():
    bulkhead = Bulkhead(max_concurrent=5)
    stats = bulkhead.stats()
    assert stats["max_concurrent"] == 5
    assert stats["current"] == 0
    assert stats["rejected"] == 0

@pytest.mark.asyncio
async def test_bulkhead_rejected_counter_increments():
    bulkhead = Bulkhead(max_concurrent=1, max_queue_size=0)
    await bulkhead.acquire()  # hold the only slot
    result = await bulkhead.acquire()
    assert result is False
    assert bulkhead._rejected == 1


# ============================================================================
# TimeoutCascade tests
# ============================================================================

def test_timeout_cascade_initial_remaining():
    cascade = TimeoutCascade(10.0)
    assert cascade.remaining() > 9.5  # some time elapsed but still positive

@pytest.mark.asyncio
async def test_timeout_cascade_check_raises_when_exhausted():
    cascade = TimeoutCascade(0.01)
    await asyncio.sleep(0.015)  # wait past deadline
    with pytest.raises(asyncio.TimeoutError, match="Timeout budget exhausted"):
        cascade.check()

def test_timeout_cascade_remaining_never_negative():
    cascade = TimeoutCascade(0.001)
    time.sleep(0.1)
    assert cascade.remaining() == 0.0

@pytest.mark.asyncio
async def test_timeout_cascade_wrap_enforces_timeout():
    cascade = TimeoutCascade(0.05)

    async def slow_func():
        await asyncio.sleep(0.1)
        return "done"

    wrapped = cascade.wrap(slow_func())
    with pytest.raises(asyncio.TimeoutError):
        await wrapped

@pytest.mark.asyncio
async def test_timeout_cascade_wrap_success_before_deadline():
    cascade = TimeoutCascade(1.0)

    async def quick_func():
        await asyncio.sleep(0.01)
        return "ok"

    wrapped = cascade.wrap(quick_func())
    result = await wrapped
    assert result == "ok"

def test_timeout_cascade_context_manager():
    async def run_with_cascade():
        cascade = TimeoutCascade(1.0)
        async with cascade:
            assert cascade.remaining() > 0
        # After exit, nothing special happens
    asyncio.run(run_with_cascade())

@pytest.mark.asyncio
async def test_timeout_cascade_wrap_propagates_other_exceptions():
    cascade = TimeoutCascade(1.0)

    async def failing_func():
        raise ValueError("test error")

    wrapped = cascade.wrap(failing_func())
    with pytest.raises(ValueError, match="test error"):
        await wrapped


# ============================================================================
# Global registry tests
# ============================================================================

def setup_function():
    """Clear global registries before each test."""
    from core_engine.resilience import _global_breakers, _global_bulkheads, _global_fallbacks
    _global_breakers.clear()
    _global_bulkheads.clear()
    _global_fallbacks.clear()

def test_register_and_get_circuit_breaker():
    breaker = CircuitBreaker("my-breaker")
    register_circuit_breaker("my-breaker", breaker)
    retrieved = get_circuit_breaker("my-breaker")
    assert retrieved is breaker

def test_get_circuit_breaker_missing():
    assert get_circuit_breaker("nonexistent") is None

def test_register_and_get_bulkhead():
    bulkhead = Bulkhead(max_concurrent=5)
    register_bulkhead("my-bulkhead", bulkhead)
    assert get_bulkhead("my-bulkhead") is bulkhead

def test_get_bulkhead_missing():
    assert get_bulkhead("nonexistent") is None

def test_register_fallback():
    async def dummy_strategy():
        return "ok"
    chain = FallbackChain(dummy_strategy)
    register_fallback("my-fallback", chain)
    from core_engine.resilience import _global_fallbacks
    assert _global_fallbacks["my-fallback"] is chain


# ============================================================================
# create_guarded_backend tests
# ============================================================================

def test_create_guarded_backend_returns_callable():
    async def backend(x):
        return x * 2
    guarded = create_guarded_backend("test-backend", backend)
    assert callable(guarded)

@pytest.mark.asyncio
async def test_create_guarded_backend_successful_call():
    async def backend(x):
        return x * 10

    guarded = create_guarded_backend("test-backend", backend)
    result = await guarded(5)
    assert result == 50

@pytest.mark.asyncio
async def test_create_guarded_backend_applies_bulkhead_limit():
    """Bulkhead permits up to max_concurrent concurrent calls."""
    async def slow_backend(x):
        await asyncio.sleep(0.1)
        return x

    max_conc = 2
    guarded = create_guarded_backend(
        "test-backend",
        slow_backend,
        bulkhead_max=max_conc,
        timeout_seconds=1.0,
    )

    # Launch more than max_concurrent tasks
    sem = asyncio.Semaphore(0)
    results = []

    async def caller(val):
        try:
            res = await guarded(val)
            results.append(("ok", val, res))
        except RuntimeError as e:
            if "Bulkhead reject" in str(e):
                results.append(("rejected", val, None))
            else:
                raise
        finally:
            sem.release()

    tasks = [asyncio.create_task(caller(i)) for i in range(5)]
    await asyncio.wait_for(asyncio.gather(*tasks), timeout=2.0)

    # With bulkhead=2 and 5 callers, we should see some rejections
    rejected = [r for r in results if r[0] == "rejected"]
    succeeded = [r for r in results if r[0] == "ok"]
    assert len(rejected) > 0
    assert len(succeeded) <= max_conc

@pytest.mark.asyncio
async def test_create_guarded_backend_with_fallbacks():
    """When primary fails, fallback chain is used."""
    primary_called = []
    fallback_called = []

    async def primary(x):
        primary_called.append(x)
        raise ValueError("primary down")

    async def fallback(x):
        fallback_called.append(x)
        return x * 3

    guarded = create_guarded_backend(
        "test-backend",
        primary,
        fallbacks=[fallback],
    )

    result = await guarded(7)
    assert result == 21  # from fallback
    assert len(primary_called) == 1
    assert len(fallback_called) == 1

@pytest.mark.asyncio
async def test_create_guarded_backend_timeout_budget():
    """TimeoutCascade enforces total timeout budget."""
    async def slow_backend(x):
        await asyncio.sleep(1.0)
        return x

    guarded = create_guarded_backend(
        "test-backend",
        slow_backend,
        timeout_seconds=0.05,
    )

    with pytest.raises(asyncio.TimeoutError):
        await guarded(1)

@pytest.mark.asyncio
async def test_create_guarded_backend_circuit_breaker_trips():
    """Circuit breaker trips after configured failures."""
    failures = 0
    cfg = CircuitBreakerConfig(failure_threshold=2)

    async def always_fail(x):
        nonlocal failures
        failures += 1
        raise ValueError("fail")

    guarded = create_guarded_backend(
        "test-backend",
        always_fail,
        breaker_config=cfg,
        timeout_seconds=1.0,
    )

    # First two calls should fail and trip breaker
    with pytest.raises(ValueError):
        await guarded(1)
    with pytest.raises(ValueError):
        await guarded(2)

    # Breaker should now be open
    from core_engine.resilience import get_circuit_breaker
    breaker = get_circuit_breaker("test-backend")
    assert breaker is not None
    assert breaker.state == CircuitState.OPEN

    # Next call is rejected immediately
    with pytest.raises(RuntimeError, match="Circuit 'test-backend' is OPEN"):
        await guarded(3)

"""
Core Engine — Resilience Patterns
Circuit breakers, fallback chains, bulkheads, and timeout cascading.
Wraps external calls and internal backends to prevent cascading failures.
"""

import asyncio
import time
import logging
import functools
from typing import Dict, List, Optional, Any, Callable, Awaitable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger("hardwareless.resilience")

T = TypeVar('T')


class CircuitState(Enum):
    """State of a circuit breaker."""
    CLOSED = "closed"       # Normal operation, requests pass through
    OPEN = "open"           # Failing, reject requests immediately
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5        # Consecutive failures to trip
    recovery_timeout_seconds: float = 30.0  # Wait before half-open
    expected_exception: tuple = (Exception,)
    # Metrics
    window_size: int = 100            # Number of recent calls to consider for rate
    minimum_calls: int = 10           # Min calls before evaluating health
    slow_call_threshold_seconds: float = 5.0  # Slow call = warning
    # Advanced
    on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None


class CircuitBreaker:
    """
    Classic circuit breaker with half-open recovery.
    Tracks recent call outcomes and trips when failure rate exceeds threshold.
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        
        # Call history
        self._recent_calls: deque[bool] = deque(maxlen=self.config.window_size)  # True=success
        self._consecutive_failures = 0
        self._last_failure_time: Optional[float] = None
        self._total_calls = 0
        self._total_failures = 0
        self._total_slow_calls = 0
    
    def record_success(self):
        """Record a successful call."""
        self._consecutive_failures = 0
        self._recent_calls.append(True)
        self._total_calls += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.CLOSED)
    
    def record_failure(self):
        """Record a failed call."""
        self._consecutive_failures += 1
        self._recent_calls.append(False)
        self._total_calls += 1
        self._total_failures += 1
        self._last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED and self._consecutive_failures >= self.config.failure_threshold:
            self._transition_to(CircuitState.OPEN)
        elif self.state == CircuitState.HALF_OPEN:
            # Half-open test failed — back to open
            self._transition_to(CircuitState.OPEN)
    
    def record_timeout(self):
        """Record a timeout (treated as failure)."""
        self.record_failure()
    
    def record_slow_call(self, duration_seconds: float):
        """Record a slow call (metrics only, not a failure)."""
        if duration_seconds > self.config.slow_call_threshold_seconds:
            self._total_slow_calls += 1
    
    def can_execute(self) -> bool:
        """
        Check if call should be allowed.
        Returns False if OPEN (rejects immediately).
        """
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout elapsed
            if (self._last_failure_time and
                (time.time() - self._last_failure_time) >= self.config.recovery_timeout_seconds):
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False
        return True
    
    def _transition_to(self, new_state: CircuitState):
        old = self.state
        self.state = new_state
        logger.warning(f"CircuitBreaker '{self.name}' state: {old.value} → {new_state.value}")
        if self.config.on_state_change:
            try:
                self.config.on_state_change(self.name, old, new_state)
            except Exception:
                pass
    
    def health_score(self) -> float:
        """
        Compute health as fraction of recent successes.
        Returns 0.0–1.0.
        """
        if not self._recent_calls:
            return 1.0  # Assume healthy if no data
        successes = sum(1 for ok in self._recent_calls if ok)
        return successes / len(self._recent_calls)
    
    def stats(self) -> Dict[str, Any]:
        """Return statistics for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "consecutive_failures": self._consecutive_failures,
            "slow_calls": self._total_slow_calls,
            "health": self.health_score(),
            "recent_success_rate": self.health_score(),
        }


class CircuitBreakerMiddleware:
    """
    Decorator/wrapper for async functions.
    Usage:
        @CircuitBreakerMiddleware("translation", config)
        async def translate(...):
            ...
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.breaker = CircuitBreaker(name, config or CircuitBreakerConfig())
    
    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            if not self.breaker.can_execute():
                raise RuntimeError(
                    f"Circuit '{self.breaker.name}' is OPEN — "
                    f"service unavailable"
                )
            
            try:
                # Execute with timeout context if needed
                result = await func(*args, **kwargs)
                self.breaker.record_success()
                return result
            except self.breaker.config.expected_exception as e:
                self.breaker.record_failure()
                raise
            except asyncio.TimeoutError as e:
                self.breaker.record_timeout()
                raise
        
        # Attach breaker for introspection
        wrapper.breaker = self.breaker  # type: ignore
        return wrapper


class FallbackChain(Generic[T]):
    """
    Chains multiple callables; tries each until one succeeds.
    Stops on first success. All failures propagate if all fail.
    """
    
    def __init__(
        self,
        *strategies: Callable[..., Awaitable[T]],
        fallback_exceptions: tuple = (Exception,),
    ):
        """
        strategies: ordered list of async callables with same signature.
        Usage:
        FallbackChain(
            lambda x: backend_a.translate(x),
            lambda x: backend_b.translate(x),
            lambda x: cached_fallback(x),
        )
        """
        self.strategies = strategies
        self.fallback_exceptions = fallback_exceptions
        self._attempts = []  # Track which strategy succeeded for last call
    
    async def execute(self, *args, **kwargs) -> T:
        """Try strategies in order until success."""
        last_exception = None
        self._attempts = []
        
        for idx, strategy in enumerate(self.strategies):
            try:
                result = await strategy(*args, **kwargs)
                self._attempts.append(idx)
                return result
            except self.fallback_exceptions as e:
                last_exception = e
                continue
        
        raise RuntimeError("All fallback strategies failed") from last_exception
    
    def last_used_index(self) -> Optional[int]:
        """Return index of strategy that succeeded last call (or None)."""
        return self._attempts[-1] if self._attempts else None


class Bulkhead:
    """
    Limits concurrent executions of a critical section.
    Uses asyncio.Semaphore. Rejects when full (fast-fail).
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        max_queue_size: Optional[int] = None,
    ):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue_size = max_queue_size
        self._current = 0
        self._rejected = 0
    
    async def acquire(self) -> bool:
        """
        Try to acquire a bulkhead slot.
        Returns False if at capacity and queue full (immediate reject).
        """
        if self._queue_size is not None and self._current >= self._queue_size:
            self._rejected += 1
            return False
        
        try:
            await self._semaphore.acquire()
            self._current += 1
            return True
        except asyncio.CancelledError:
            raise
    
    def release(self):
        self._semaphore.release()
        self._current -= 1
    
    def stats(self) -> Dict[str, int]:
        return {
            "max_concurrent": self.max_concurrent,
            "current": self._current,
            "rejected": self._rejected,
        }
    
    async def __aenter__(self):
        if not await self.acquire():
            raise RuntimeError("Bulkhead full — request rejected")
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        self.release()


class TimeoutCascade:
    """
    Propagates timeout budget through nested calls.
    Each call receives the remaining time; child tasks fail fast when budget exhausted.
    """
    
    def __init__(self, total_seconds: float):
        self.total_budget = total_seconds
        self._start_time = time.monotonic()
        self._deadline = self._start_time + total_seconds
    
    def remaining(self) -> float:
        """Seconds remaining before timeout."""
        return max(0.0, self._deadline - time.monotonic())
    
    def check(self) -> None:
        """Raise TimeoutError if budget exhausted."""
        if self.remaining() <= 0:
            raise asyncio.TimeoutError("Timeout budget exhausted")
    
    def wrap(self, coro: Awaitable[T]) -> Awaitable[T]:
        """
        Wrap an awaitable to fail on timeout budget exhaustion.
        Usage: await cascade.wrap(some_async_call())
        """
        async def wrapped():
            self.check()
            # Enforce remaining time via asyncio.wait_for
            remaining = self.remaining()
            if remaining <= 0:
                raise asyncio.TimeoutError("Timeout budget exhausted")
            try:
                return await asyncio.wait_for(coro, timeout=remaining)
            except asyncio.TimeoutError:
                raise
        return wrapped()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        pass


# Global registry of breakers and bulkheads
_global_breakers: Dict[str, CircuitBreaker] = {}
_global_bulkheads: Dict[str, Bulkhead] = {}
_global_fallbacks: Dict[str, FallbackChain] = {}


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    return _global_breakers.get(name)


def get_bulkhead(name: str) -> Optional[Bulkhead]:
    return _global_bulkheads.get(name)


def register_circuit_breaker(name: str, breaker: CircuitBreaker) -> None:
    _global_breakers[name] = breaker


def register_bulkhead(name: str, bulkhead: Bulkhead) -> None:
    _global_bulkheads[name] = bulkhead


def register_fallback(name: str, chain: FallbackChain) -> None:
    _global_fallbacks[name] = chain


# Integration helper: create guarded translation backend
def create_guarded_backend(
    backend_name: str,
    backend_func: Callable[..., Awaitable[T]],
    *,
    breaker_config: Optional[CircuitBreakerConfig] = None,
    bulkhead_max: int = 10,
    timeout_seconds: float = 30.0,
    fallbacks: Optional[List[Callable[..., Awaitable[T]]]] = None,
) -> Callable[..., Awaitable[T]]:
    """
    Wrap a backend function with resilience patterns.
    Returns a guarded function that applies circuit breaking, bulkhead limits,
    timeout cascade (optional), and fallback chain.
    """
    # Register components
    breaker = CircuitBreaker(backend_name, config=breaker_config)
    register_circuit_breaker(backend_name, breaker)
    
    bulkhead = Bulkhead(max_concurrent=bulkhead_max)
    register_bulkhead(backend_name, bulkhead)
    
    # Wrap with breaking
    @CircuitBreakerMiddleware(backend_name, breaker_config)
    async def guarded(*args, **kwargs):
        # Bulkhead check
        if not await bulkhead.acquire():
            raise RuntimeError(f"Bulkhead reject for {backend_name}")
        try:
            cascade = TimeoutCascade(timeout_seconds)
            async with cascade:
                result = await cascade.wrap(backend_func(*args, **kwargs))
            return result
        finally:
            bulkhead.release()
    
    # If fallbacks provided, wrap in FallbackChain
    if fallbacks:
        chain = FallbackChain(guarded, *fallbacks)
        register_fallback(backend_name, chain)
        return chain.execute  # type: ignore
    
    return guarded


__all__ = [
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreaker",
    "CircuitBreakerMiddleware",
    "FallbackChain",
    "Bulkhead",
    "TimeoutCascade",
    "get_circuit_breaker",
    "get_bulkhead",
    "register_circuit_breaker",
    "register_bulkhead",
    "register_fallback",
    "create_guarded_backend",
]

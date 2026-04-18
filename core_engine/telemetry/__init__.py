"""
Core Engine — Telemetry & Observability
Unified structured logging, metrics (Prometheus), tracing (OpenTelemetry), and health aggregation.
Designed as a plugin that can also be used as a library by other plugins.
"""

import json
import time
import uuid
import logging
import threading
import contextlib
from typing import Dict, List, Optional, Any, Tuple, ContextManager
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

# Structured logging helper
class StructuredLogger:
    """
    Wrapper around standard logging that emits JSON lines with context.
    Each log record includes: timestamp, level, service, trace_id, span_id, message, extra.
    """
    
    def __init__(self, name: str, service: str = "hardwareless-ai"):
        self.logger = logging.getLogger(name)
        self.service = service
        self._local = threading.local()
    
    def _get_context(self) -> Dict[str, Any]:
        """Get current tracing context (trace_id, span_id) from thread-local."""
        ctx = {}
        if hasattr(self._local, "trace_id"):
            ctx["trace_id"] = self._local.trace_id
        if hasattr(self._local, "span_id"):
            ctx["span_id"] = self._local.span_id
        if hasattr(self._local, "request_id"):
            ctx["request_id"] = self._local.request_id
        return ctx
    
    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs: Any):
        record_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": logging.getLevelName(level),
            "service": self.service,
            "message": message,
        }
        # Merge context
        record_data.update(self._get_context())
        # Merge extra/kwargs
        if extra:
            record_data.update(extra)
        record_data.update(kwargs)
        
        self.logger.log(level, json.dumps(record_data))
    
    def debug(self, msg: str, **kwargs: Any):
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs: Any):
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs: Any):
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs: Any):
        self._log(logging.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs: Any):
        self._log(logging.CRITICAL, msg, **kwargs)
    
    @contextlib.contextmanager
    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a traced span (no-op if no tracer configured)."""
        old_trace = getattr(self._local, "trace_id", None)
        old_span = getattr(self._local, "span_id", None)
        
        # Generate IDs if not already tracing
        if old_trace is None:
            self._local.trace_id = str(uuid.uuid4())
        else:
            self._local.trace_id = old_trace
        
        new_span = str(uuid.uuid4())
        self._local.span_id = new_span
        
        start = time.time()
        try:
            yield
        finally:
            elapsed = (time.time() - start) * 1000
            # Log span end
            span_data = {
                "span.name": name,
                "span.id": new_span,
                "span.duration_ms": round(elapsed, 2),
            }
            if attributes:
                span_data.update({f"span.attr.{k}": v for k, v in attributes.items()})
            self.debug(f"span.end {name}", extra=span_data)
            # Restore context
            if old_trace is not None:
                self._local.trace_id = old_trace
            if old_span is not None:
                self._local.span_id = old_span
            else:
                delattr(self._local, "span_id")


# Prometheus-style metrics collector
class MetricsCollector:
    """
    In-process metrics (counters, gauges, histograms, summaries).
    Can be scraped by Prometheus or exported via /metrics endpoint.
    Thread-safe. Minimal overhead.
    """
    
    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._summaries: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()
    
    # Counter
    def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        key = self._tag_key(name, tags)
        with self._lock:
            self._counters[key] += value
    
    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        key = self._tag_key(name, tags)
        return self._counters.get(key, 0.0)
    
    # Gauge
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        key = self._tag_key(name, tags)
        with self._lock:
            self._gauges[key] = float(value)
    
    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        key = self._tag_key(name, tags)
        return self._gauges.get(key, 0.0)
    
    # Histogram (for latency, size distributions)
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        key = self._tag_key(name, tags)
        with self._lock:
            self._histogram_values(key).append(float(value))
            # Keep last 1000 samples to bound memory
            if len(self._histogram_values(key)) > 1000:
                self._histogram_values(key).pop(0)
    
    def _histogram_values(self, key: str) -> List[float]:
        return self._histograms.setdefault(key, [])
    
    def histogram_stats(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        key = self._tag_key(name, tags)
        values = self._histogram_values(key)
        if not values:
            return {"count": 0}
        values.sort()
        n = len(values)
        return {
            "count": n,
            "sum": sum(values),
            "min": values[0],
            "max": values[-1],
            "avg": sum(values) / n,
            "p50": values[int(n * 0.50)],
            "p95": values[int(n * 0.95)],
            "p99": values[int(n * 0.99)],
        }
    
    # Tag handling
    def _tag_key(self, name: str, tags: Optional[Dict[str, str]]) -> str:
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}{{{tag_str}}}"
        return name
    
    # Export for Prometheus text format
    def export_prometheus(self) -> str:
        """Generate Prometheus exposition format."""
        lines = []
        # Counters
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        # Gauges
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        # Histograms (as summaries for now, buity)
        for name, values in self._histograms.items():
            if not values:
                continue
            # Export as summary
            lines.append(f"# TYPE {name} summary")
            lines.append(f"{name}_sum {sum(values)}")
            lines.append(f"{name}_count {len(values)}")
            # Quantiles (approximate from sorted list)
            sorted_vals = sorted(values)
            for quantile in [0.5, 0.95, 0.99]:
                idx = int(len(sorted_vals) * quantile)
                val = sorted_vals[idx] if idx < len(sorted_vals) else sorted_vals[-1]
                lines.append(f"{name}_quantile{{quantile=\"{quantile}\"}} {val}")
        return "\n".join(lines) + "\n"
    
    def clear(self):
        """Reset all metrics (useful between tests)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._summaries.clear()


# Health aggregator
@dataclass
class ComponentHealth:
    """Health status for a single component."""
    name: str
    healthy: bool
    state: str
    message: Optional[str] = None
    last_check: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    details: Dict[str, Any] = field(default_factory=dict)


class HealthAggregator:
    """
    Aggregates health across all plugins, subsystems, external dependencies.
    Used by the /health endpoint and monitoring systems.
    """
    
    def __init__(self):
        self._components: Dict[str, ComponentHealth] = {}
        self._lock = threading.RLock()
    
    def register(self, name: str, initial: Optional[ComponentHealth] = None) -> None:
        with self._lock:
            if initial:
                self._components[name] = initial
            else:
                self._components[name] = ComponentHealth(
                    name=name, healthy=True, state="unknown"
                )
    
    def update(self, name: str, healthy: bool, state: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        with self._lock:
            if name not in self._components:
                self.register(name)
            comp = self._components[name]
            comp.healthy = healthy
            comp.state = state
            comp.message = message
            comp.last_check = datetime.utcnow().isoformat() + "Z"
            if details:
                comp.details.update(details)
    
    def get_overall(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Determine overall system health.
        Returns (is_healthy, report_dict).
        """
        with self._lock:
            healthy = all(c.healthy for c in self._components.values())
            report = {
                "status": "healthy" if healthy else "degraded",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "components": {name: asdict(c) for name, c in self._components.items()},
            }
            return healthy, report
    
    def get_component(self, name: str) -> Optional[ComponentHealth]:
        with self._lock:
            return self._components.get(name)


# Profiler middleware helper — lightweight request timing
class RequestProfiler:
    """
    Context manager for profiling request/operation duration.
    Records histograms and optionally full trace data.
    """
    
    def __init__(self, metrics: MetricsCollector, name: str, tags: Optional[Dict[str, str]] = None):
        self.metrics = metrics
        self.name = name
        self.tags = tags or {}
        self.start: Optional[float] = None
    
    def __enter__(self) -> "RequestProfiler":
        self.start = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start is not None:
            elapsed_ms = (time.perf_counter() - self.start) * 1000
            self.metrics.record_histogram(self.name, elapsed_ms, tags=self.tags)
            # Also record as counter bucketed
            self.metrics.increment_counter(f"{self.name}_total", tags=self.tags)


# Singleton instances (colocated for convenience)
_global_logger = StructuredLogger("hardwareless")
_global_metrics = MetricsCollector()
_global_health = HealthAggregator()

def get_logger() -> StructuredLogger:
    return _global_logger

def get_metrics() -> MetricsCollector:
    return _global_metrics

def get_health() -> HealthAggregator:
    return _global_health

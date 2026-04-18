# Comprehensive Test Plan — Hardwareless AI Expansion

## File-by-File Coverage Gap Analysis

### 1. Syntax Blocker (Immediate Fix)
- ✅ **`core_engine/translation/language_detection.py:24`** — Fixed: `self._ngram fingerprints` → `self._ngram_fingerprints`

---

### 2. Plugin System (`core_engine/plugins/`) — 0% Coverage

**Files:**
- `base.py` (230 stmts) — BasePlugin, PluginManifest, PluginContext, PluginState
- `registry.py` (307 stmts) — PluginRegistry, discovery, load_plugin, resolve_load_order
- `manager.py` (236 stmts) — PluginManager, aggregate_health, load_all lifecycle
- `specializations.py` (272 stmts) — TranslatorBackendPlugin, CompressionPlugin, CachePlugin, ObservabilityPlugin, SecurityPlugin
- `__init__.py` (4 stmts) — exports

**Test Files to Create:**
```
tests/plugins/
  __init__.py
  test_base.py               # PluginManifest, BasePlugin lifecycle, PluginContext
  test_registry.py           # PluginRegistry.register, get_plugin, get_by_capability, load order
  test_manager.py            # PluginManager.discover, load_all, aggregate_health
  test_specializations.py    # Each abstract base's contract
  fixtures/
    sample_plugin.py         # Mock plugin implementations for testing
```

**Key test scenarios:**
- Manifest serialization/deserialization (to_dict/from_dict)
- Discovery from directory with valid/invalid `plugin.json`
- Discovery from entry points (mocked importlib.metadata)
- Dependency resolution: topological sort handles circular deps, missing deps
- Load order respects PluginPriority + dependencies
- Plugin lifecycle: `initialize()` called async, state transitions (LOADING→ACTIVE)
- Failed plugin handling: exceptions caught, state set to FAILED, others continue
- `aggregate_health()` aggregates all plugin health_check() results
- Capability filtering returns only active plugins
- Context methods: `get_plugin()`, `require_plugin()` raise when missing

---

### 3. Connection Pooling (`core_engine/connections/`) — 0% Coverage

**Files:**
- `pool.py` (242 stmts) — ConnectionPool, PooledConnection, PoolConfig, AIOHTTPConnectionPool, GenericPoolManager
- `batcher.py` (137 stmts) — RequestBatcher, TranslationBatcher, @batched decorator
- `__init__.py` (3 stmts) — exports

**Test Files:**
```
tests/connections/
  __init__.py
  test_pool.py               # ConnectionPool acquire/release, exhaustion, health checks
  test_aiohttp_pool.py       # AIOHTTPConnectionPool concrete behavior
  test_batcher.py            # RequestBatcher flush timing, size limits
  test_batched_decorator.py  # @batched consolidates calls correctly
  fixtures/
    mock_connection.py       # Simple mock connection for testing
```

**Key scenarios:**
- `PoolConfig` defaults
- `ConnectionPool.initialize()` starts health task
- `acquire()` waits if pool empty (with timeout)
- `release()` returns connection to queue
- `PooledConnection.mark_used()` updates timestamps
- `is_stale()` identifies idle connections > max_idle_time
- Health check loop culls dead connections
- `AIOHTTPConnectionPool._create_connection()` creates aiohttp.ClientSession
- `RequestBatcher`: items batch on size OR interval
- `flush()` processes batch, clears queue
- Timeout forces flush even if batch not full
- `@batched` decorator wraps function, batches concurrent calls with same key
- `TranslationBatcher` groups by language pair (src→tgt)

---

### 4. Intelligent Caching (`core_engine/cache/`) — 0% Coverage

**Files:**
- `manager.py` (appears in coverage but 0 stmts counted? Need to verify file exists and is importable)

**Test Files:**
```
tests/cache/
  __init__.py
  test_cache_manager.py      # CacheManager get/set/delete, namespaces, TTL
  test_backends.py           # MemoryLRU, RedisCluster, DiskCache (mocked)
  test_cache_aside.py        # @cache_aside decorator behavior
  test_warming.py            # Warmer registration + warm_namespace()
```

**Key scenarios:**
- `CacheManager` initialization
- `get(key)` returns cached value or None
- `set(key, value, ttl)` stores in appropriate tier
- Namespace isolation: `ns:key1` vs `ns:key2` don't collide
- Composite cascade: memory miss → Redis → disk miss → loader
- `MemoryLRUBackend` evicts LRU entry when capacity reached
- `RedisClusterBackend` uses redis client (mock with fakeredis)
- `DiskCacheBackend` serializes with pickle, writes to `.cache/` dir
- `cache_aside` decorator: on miss calls loader, stores result
- Warming: `register_warmer(name, callback)` stores callback; `warm_namespace()` runs all warmers
- Metrics: hit count, miss count tracked per backend

---

### 5. Resilience (`core_engine/resilience/__init__.py`) — 0% Coverage

**Test Files:**
```
tests/resilience/
  __init__.py
  test_circuit_breaker.py    # State CLOSED→OPEN→HALF_OPEN, failure threshold
  test_fallback_chain.py     # Tries each fallback until success
  test_bulkhead.py           # Semaphore limits concurrent executions
  test_timeout_cascade.py    # Nested timeouts propagate correctly
  test_guarded_backend.py    # create_guarded_backend() composes all patterns
```

**Key scenarios:**
- `CircuitBreaker`: failures > threshold → OPEN; OPEN ignores calls fast; HALF_OPEN allows test request; success → CLOSED
- `CircuitBreakerMiddleware`: endpoint raises 503 when breaker open
- `FallbackChain`: calls fallbacks in order, returns first success
- `Bulkhead`: semaphore acquired on enter, released on exit; rejects when full
- `TimeoutCascade`: parent timeout encompasses child operations
- `create_guarded_backend()` wraps function with all: bulkhead → timeout → circuit breaker → fallback

---

### 6. Developer Tools (`core_engine/devtools/`) — 0% Coverage

**Test Files:**
```
tests/devtools/
  __init__.py
  test_request_logger.py     # RequestLog captures method/path/timing, sanitizes headers
  test_hot_reload.py         # KnowledgeBaseHotReloader watches file, triggers callback
  test_dev_toolbar.py        # DevToolbarMiddleware injects HTML overlay on HTML responses
```

**Key scenarios:**
- `RequestLogger` middleware: logs request start/end with timing; strips Authorization headers
- `KnowledgeBaseHotReloader`: uses watchdog to monitor file changes; calls `reload_knowledge()` on change
- `DevToolbarMiddleware`: enabled only when `DEV_MODE=1`; injects toolbar HTML before `</body>`; works with both string and JSON responses (only injects into HTML content-type)
- `DebugModeExtension`: conditional on env var

---

### 7. Advanced Security (`core_engine/security/advanced.py`) — 23% → 100%

**Missing coverage:**
- CSRF token generation/validation
- Fingerprint hashing & bot scoring
- PII redaction patterns (SSN, CC, email)
- SecretsVault backends (HashiCorp, AWS)
- ThreatFeed async polling and blocking decisions

**Test Files:**
```
tests/security/
  test_csrf.py               # CSRFToken, CSRFMiddleware validation
  test_fingerprint.py        # Fingerprint, BotScorer
  test_pii_redactor.py       # PIIRedactor regex patterns
  test_vaults.py             # EnvFileVault, HashiCorpVault, AWSSecretsManagerBackend (mocked)
  test_threat_feed.py        # ThreatFeed update, is_blocked, IP/UA matching
```

---

### 8. New API Routes (`gateway/routes/`) — Partial Coverage

**Files needing test expansion:**

| File | Current Cover | Tests Needed |
|------|---------------|--------------|
| `batch.py` | 34% | Test both `/v1/batch/chat` and `/v1/batch/translate`; partial failures; empty batch handling |
| `sse.py` | 23% | SSE event streaming (`/v1/stream`); event types (chunk, done, error, metrics); client disconnect handling |
| `webhooks.py` | 34% | Registration, signature verification, retry logic, delivery queue |
| `graphql.py` | 28% | Schema introspection, query resolution, errors |
| `grpc.py` | 14% | Service methods (mocked proto) |
| `legacy.py` | 28% | `/chat` POST backward-compat; WebSocket `/ws/stream` protocol |

**Test Files to extend:**
```
tests/routes/
  test_batch.py         # Expand (currently minimal)
  test_sse.py           # Expand
  test_webhooks.py      # Expand
  test_graphql.py       # Expand
  test_grpc.py          # New
  test_legacy.py        # New
```

---

### 9. Observability (`core_engine/telemetry/__init__.py`) — 0% Coverage

**Test Files:**
```
tests/telemetry/
  __init__.py
  test_logger.py          # StructuredLogger JSON output, levels
  test_metrics.py         # MetricsCollector counters/histograms/gauges
  test_health.py          # HealthAggregator aggregates subsystems
  test_profiler.py        # RequestProfiler context manager timing
```

---

### 10. Translation Backends — Low Coverage

- `backends/libretranslate.py` (20%) — add tests for aiohttp calls, error handling
- `backends/opus_mt.py` (23%) — test with ctranslate2 mocked
- `backends/mtranserver.py` (29%) — test MTran server client

**Test files:** expand `tests/translation/` if they exist, or create new.

---

### 11. Other Low-Coverage Core Modules

| Module | Stmts | Cover | Priority | Notes |
|--------|-------|-------|----------|-------|
| `core_engine/brain/backend.py` | 175 | 55% | Medium | HDC backend abstraction; test fallback logic |
| `core_engine/brain/hdc.py` | 66 | 38% | Medium | Core HDC ops; already partially tested |
| `core_engine/brain/weight.py` | 126 | 26% | Medium | ChromaWeight, attention; need tests |
| `core_engine/security/validator.py` | 152 | 39% | Medium | InputValidator, audit logger, anomaly detector — expand tests |
| `core_engine/virus_guard.py` | 246 | 40% | High | VIRUS-VDI core logic; needs more scenarios |
| `gateway/routes/health.py` | 19 | 33% | Low | Already works, but could test subsystem registration |

---

## Non-Test Fixes (Must Do While Writing Tests)

### A. Fix LSP/Type Errors in `gateway/app.py`
**Problem:** Lines 68, 73, 92, 194, 196, 198, 200 — `get_cache`, `register_subsystems`, `get_language_matrix`, `sse`, `webhooks`, `graphql`, `grpc` may be unbound due to conditional imports.

**Fix:** Wrap conditional routes in TYPE_CHECKING or move imports into try blocks where they're used.

Already handled via try/except; LSP false positive. Could add:
```python
if TYPE_CHECKING:
    from gateway.routes.sse import start_broadcaster
    ...
```

### B. Pydantic V2 Migration (4 warnings)
**Files:** `gateway/routes/chat.py:72,84,255`

Replace `@validator` with `@field_validator` and update method signatures.

### C. Add Circuit Breaker Metrics to Stats
**File:** `gateway/routes/stats.py`

Add:
```python
from core_engine.resilience import get_all_breakers
...
"circuit_breakers": {name: b.stats() for name, b in get_all_breakers().items()}
```

### D. Cache Warming Strategy
**File:** `gateway/app.py` line 77-78

Currently only one warmer. Add more:
- Common translation pairs
- Greeting responses
- Threat feed lookups

### E. `requirements.txt` Version Pinning
Generate locked file:
```bash
pip freeze > requirements.lock.txt
```

### F. `.gitignore` Check
Ensure `.env`, `__pycache__/`, `.pytest_cache/`, `frontend/.next/`, `*.log` are ignored.

---

## Implementation Order

**Phase 1 — Critical Blocker (1–2 hrs)**
1. ✅ Fix `language_detection.py` syntax — DONE
2. Add quick test for `language_detection.py` to verify coverage now counts

**Phase 2 — Foundation Infrastructure (8–12 hrs)**
3. Plugin system tests (base, registry, manager) — highest leverage (many modules depend on plugins)
4. Connection pool + batcher tests — core async infrastructure
5. Cache manager tests — another foundational layer

**Phase 3 — Advanced Features (8–12 hrs)**
6. Resilience tests — circuit breakers, bulkheads, timeouts
7. Devtools tests — logger, hot-reload, toolbar
8. Observability tests — metrics, health, profiling

**Phase 4 — Integration (4–6 hrs)**
9. API route tests — batch, SSE, webhooks, legacy
10. Advanced security tests — CSRF, fingerprint, PII, vaults, feeds

**Phase 5 — Polish (2–4 hrs)**
11. Pydantic V2 migration
12. Expose circuit breaker metrics in stats
13. Add more cache warmers
14. Generate `requirements.lock.txt`
25. Verify `.gitignore` completeness

**Total estimated effort:** 25–40 hours of test writing + 4–6 hours of polish.

---

## Metrics

| Target | Current | After Phase 2 | After Phase 3 | After Phase 4 |
|--------|---------|---------------|---------------|---------------|
| Overall coverage | 28% | 50–60% | 70%+ | 80%+ |
| Plugin coverage | 0% | 80% | — | — |
| Connections coverage | 0% | 70% | — | — |
| Cache coverage | 0% | 80% | — | — |
| Resilience coverage | 0% | — | 85% | — |
| Devtools coverage | 0% | — | 80% | — |
| Telemetry coverage | 0% | — | 80% | — |
| Routes coverage (avg) | 14–34% | — | — | 70%+ |

---

## Risk Notes

- **Async timing:** batcher flush intervals, circuit breaker timeouts — use `freezegun` or monkeypatch `time.monotonic`
- **HDC randomness:** seed numpy in test setup for reproducibility
- **Redis mocking:** use `fakeredis` for cache tests (avoid real Redis dependency)
- **File system:** hot-reload tests use `tmp_path` and `pytest`'s `monkeypatch` to simulate file changes
- **Optional dependencies:** guard GraphQL/GRPC/SSE tests with `pytest.importorskip`

---

## Conclusion

The codebase is **functionally complete** and tests pass for core functionality. The expansion introduced ~3,500 lines of infrastructure that lack test coverage. This document provides a systematic plan to achieve **80%+ coverage** by writing targeted tests for each module, prioritized by importance to system stability.

**Start with Phase 1** (fix syntax error + quick test), then Phase 2 (foundational infrastructure), then continue down the list.

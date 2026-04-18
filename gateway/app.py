"""
Hardwareless AI — Gateway Main App
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from gateway.routes import chat, health, models, stats
from gateway.routes import memory, skills, keys, websocket
from gateway.routes import agents, bridge, xr, security, virus, scam, stealth, intel, evidence
from gateway.routes import api_keys, vectors, batch

# Optional dependency routes (only import if libs available)
try:
    from gateway.routes import sse
    _SSE_AVAILABLE = True
except ImportError:
    _SSE_AVAILABLE = False

try:
    from gateway.routes import webhooks
    _WEBHOOKS_AVAILABLE = True
except ImportError:
    _WEBHOOKS_AVAILABLE = False

try:
    from gateway.routes import graphql
    _GRAPHQL_AVAILABLE = True
except ImportError:
    _GRAPHQL_AVAILABLE = False

try:
    from gateway.routes import grpc
    _GRPC_AVAILABLE = True
except ImportError:
    _GRPC_AVAILABLE = False
from gateway.middleware.auth import AuthMiddleware, RateLimitMiddleware, get_rate_limiter, get_request_signer, RequestSignatureMiddleware
from gateway.middleware.security_headers import SecurityHeadersMiddleware
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ignite the Swarm Monitor on boot."""
    # 1. Validate config & apply profile
    from config.validator import auto_apply_profile, ConfigValidator
    auto_apply_profile()
    validator = ConfigValidator()
    validator.validate_all()
    validator.log_summary()
    
    # 2. Start pluggable system
    from core_engine.plugins import get_plugin_manager
    pm = get_plugin_manager()
    app.state.plugin_manager = pm
    results = await pm.load_all()
    active_count = sum(1 for r in results if r.success)
    print(f"--- [PLUGIN] System loaded: {active_count}/{len(results)} plugins active ---")
    
    # 3. Initialize connection pools
    from core_engine.connections import get_pool_manager
    pool_mgr = get_pool_manager()
    await pool_mgr.initialize_all()
    app.state.pool_manager = pool_mgr
    
    # 4. Initialize cache & warm common namespaces
    from core_engine.cache import get_cache
    cache_mgr = get_cache()
    await cache_mgr.initialize()
    # Warm translation matrix vectors
    async def warm_translation_vectors():
        from core_engine.translation import get_language_matrix
        lm = get_language_matrix()
        # Pre-compute anchor vectors (already done in matrix init)
        return {"languages": len(lm.get_supported_languages())}
    cache_mgr.register_warmer("translation_anchors", warm_translation_vectors)
    await cache_mgr.warm_namespace("translation_anchors")
    app.state.cache = cache_mgr
    
    # 5. Initialize telemetry singleton (nothing to do — module-level)
    from core_engine.telemetry import get_logger, get_metrics, get_health
    app.state.logger = get_logger()
    app.state.metrics = get_metrics()
    app.state.health = get_health()
    
    # 6. Load threat intel feeds
    from core_engine.security.advanced import load_threat_feeds
    asyncio.create_task(load_threat_feeds())
    
    # 7. Register routes that depend on init
    from gateway.routes.health import register_subsystems
    register_subsystems({
        "plugins": lambda: pm.aggregate_health(),
        "cache": lambda: cache_mgr.stats(),
        "pools": lambda: pool_mgr.health_all(),
    })
    
    # 8. Start HypervectorServer (existing)
    from network.stream_server import HypervectorServer
    server = HypervectorServer(port=8888)
    health.swarm_server = server
    asyncio.create_task(server.start())
    print("--- [SWARM MONITOR] Mission Control Active on port 8888 ---")
    
    # 9. SSE broadcaster
    try:
        from gateway.routes.sse import start_broadcaster
        asyncio.create_task(start_broadcaster())
        print("--- [SSE] Metrics stream started ---")
    except Exception as e:
        print(f"--- [SSE] Failed to start: {e} ---")
    
    print("=== Hardwareless AI Gateway boot complete ===")
    yield
    
    # ——— Shutdown ———
    await pm.shutdown()
    await pool_mgr.shutdown_all()
    await cache_mgr.shutdown()
    try:
        from gateway.routes.sse import stop_broadcaster
        await stop_broadcaster()
    except Exception:
        pass
    print("=== Gateway shutdown complete ===")


app = FastAPI(
    title="Hardwareless AI Gateway",
    description="A GPU/CPU-less AI that moves with the data flow.",
    version="0.3.0",
    lifespan=lifespan,
)

# Security: Add security headers first
app.add_middleware(SecurityHeadersMiddleware)

# CSRF protection for state-changing requests (enabled in staging/prod)
if os.getenv("SECURITY_HEADERS_ENABLED", "1") == "1" and os.getenv("ENVIRONMENT", "development") != "development":
    try:
        from core_engine.security.advanced import CSRFMiddleware
        app.add_middleware(CSRFMiddleware)
        print("--- [SECURITY] CSRF middleware ENABLED ---")
    except ImportError:
        pass

# Enable CORS — configurable via CORS_ALLOW_ORIGINS env var (comma-separated)
default_origins = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"
cors_origins = os.getenv("CORS_ALLOW_ORIGINS", default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fingerprinting/Bot detection (low overhead)
if os.getenv("ENABLE_FINGERPRINTING", "1") == "1":
    try:
        from core_engine.security.advanced import FingerprintMiddleware
        app.add_middleware(FingerprintMiddleware)
        print("--- [SECURITY] Fingerprint middleware ENABLED ---")
    except ImportError:
        pass

# Add rate limiting
app.add_middleware(RateLimitMiddleware, limiter=get_rate_limiter())

# Add authentication (API key) — optional for dev, enforced in production
app.add_middleware(AuthMiddleware)

# Optional request signing for replay protection (disabled by default)
if os.getenv("ENABLE_REQUEST_SIGNING"):
    app.add_middleware(RequestSignatureMiddleware, signer=get_request_signer())
    print("--- [SECURITY] Request signing ENABLED ---")

# Dev tools (debug mode only)
if os.getenv("DEV_MODE") or os.getenv("DEBUG"):
    try:
        from core_engine.devtools import DevToolbarMiddleware
        app.add_middleware(DevToolbarMiddleware)
        print("--- [DEV] Dev toolbar ENABLED ---")
    except ImportError:
        pass

# Register routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(batch.router)
if _SSE_AVAILABLE:
    app.include_router(sse.router)
if _WEBHOOKS_AVAILABLE:
    app.include_router(webhooks.router)
if _GRAPHQL_AVAILABLE and os.getenv("ENABLE_GRAPHQL"):
    app.include_router(graphql.router)
if _GRPC_AVAILABLE and os.getenv("ENABLE_GRPC"):
    app.include_router(grpc.router)
app.include_router(models.router)
app.include_router(stats.router)
app.include_router(memory.router)
app.include_router(skills.router)
app.include_router(keys.router)
app.include_router(websocket.router)
app.include_router(agents.router)
app.include_router(bridge.router)
app.include_router(xr.router)
app.include_router(security.router)
app.include_router(virus.router)
app.include_router(scam.router)
app.include_router(stealth.router)
app.include_router(intel.router)
app.include_router(evidence.router)
app.include_router(api_keys.router)
app.include_router(vectors.router)

if __name__ == "__main__":
    import uvicorn
    print("Booting Hardwareless AI Gateway on port 8000...")
    uvicorn.run("gateway.app:app", host="0.0.0.0", port=8000, reload=True)

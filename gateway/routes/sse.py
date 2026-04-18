"""
Gateway — Server-Sent Events (SSE) Streaming
Real-time metrics, health updates, and swarm events.
Optional dependency: sse-starlette
"""

import os
import time
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

logger = logging.getLogger("hardwareless.sse")

# Check for optional dependency
try:
    from sse_starlette.sse import EventSourceResponse
    _SSE_AVAILABLE = True
except ImportError:
    _SSE_AVAILABLE = False

router = APIRouter(prefix="/v1/stream", tags=["sse"])

if not _SSE_AVAILABLE:
    logger.warning("sse-starlette not installed; SSE endpoint disabled")
    
    @router.get("/")
    async def sse_unavailable():
        return JSONResponse({"error": "SSE not available. Install sse-starlette."}, status_code=503)
    
    async def start_broadcaster(): pass
    async def stop_broadcaster(): pass
    async def broadcast_swarm_incident(*args, **kwargs): pass
    
else:
    # Global state to broadcast
    from core_engine.telemetry import get_metrics, get_health
    from gateway.routes.health import swarm_server
    
    _subscribers: List[asyncio.Queue] = []
    _subscribers_lock = asyncio.Lock()
    _broadcaster_task: Optional[asyncio.Task] = None
    
    async def _broadcast(event_type: str, data: Dict[str, Any]):
        async with _subscribers_lock:
            dead = []
            for queue in _subscribers:
                try:
                    event = {"type": event_type, "data": data, "ts": time.time()}
                    await queue.put(event)
                except Exception:
                    dead.append(queue)
            for q in dead:
                _subscribers.remove(q)
    
    async def metrics_broadcaster():
        while True:
            await asyncio.sleep(5)
            try:
                m = get_metrics()
                h = get_health()
                metrics_data = {
                    "counters": dict(m._counters),
                    "gauges": m._gauges.copy(),
                    "histograms": {k: m.histogram_stats(k) for k in m._histograms.keys()},
                }
                health_data = None
                try:
                    _, report = h.get_overall()
                    health_data = report
                except Exception:
                    pass
                await _broadcast("metrics", {"metrics": metrics_data, "health": health_data})
            except Exception as e:
                logger.error(f"Metrics broadcaster error: {e}")
    
    async def start_broadcaster():
        global _broadcaster_task
        _broadcaster_task = asyncio.create_task(metrics_broadcaster())
        logger.info("SSE metrics broadcaster started")
    
    async def stop_broadcaster():
        global _broadcaster_task
        if _broadcaster_task:
            _broadcaster_task.cancel()
            try:
                await _broadcaster_task
            except asyncio.CancelledError:
                pass
    
    @router.get("/")
    async def sse_events(request: Request, types: Optional[str] = None):
        allowed = set(types.split(",")) if types else None
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with _subscribers_lock:
            _subscribers.append(queue)
        
        async def event_generator():
            try:
                yield {"event": "connected", "data": json.dumps({"client_id": str(id(queue))})}
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30)
                        if allowed and event["type"] not in allowed:
                            continue
                        yield {"event": event["type"], "data": json.dumps(event["data"])}
                    except asyncio.TimeoutError:
                        yield {"event": "ping", "data": json.dumps({"ts": time.time()})}
            finally:
                async with _subscribers_lock:
                    if queue in _subscribers:
                        _subscribers.remove(queue)
        
        return EventSourceResponse(event_generator())
    
    @router.post("/trigger/{event_type}")
    async def trigger_event(event_type: str, payload: Dict[str, Any]):
        await _broadcast(event_type, payload)
        return {"ok": True, "event": event_type}
    
    def broadcast_swarm_incident(incident_type: str, details: Dict[str, Any]):
        asyncio.create_task(_broadcast("incident", {"incident": incident_type, "details": details}))


__all__ = ["router", "start_broadcaster", "stop_broadcaster", "broadcast_swarm_incident"]

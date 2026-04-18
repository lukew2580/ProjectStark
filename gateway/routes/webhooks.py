"""
Gateway — Webhook System
Register callbacks for system events, retry on failure, batched delivery.
Optional dependency: aiohttp for delivery.
"""

import os
import time
import json
import uuid
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("hardwareless.webhooks")

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])

# Check for aiohttp
try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False
    aiohttp = None  # type: ignore


class WebhookEvent(Enum):
    """System events that can trigger webhooks."""
    CHAT_COMPLETED = "chat.completed"
    TRANSLATION_COMPLETED = "translation.completed"
    SENTINEL_BLOCKED = "sentinel.blocked"
    ANOMALY_DETECTED = "anomaly.detected"
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_FAILED = "plugin.failed"
    HEALTH_CHANGE = "health.change"
    SYSTEM_START = "system.start"
    SYSTEM_SHUTDOWN = "system.shutdown"


@dataclass
class WebhookRegistration:
    """A registered webhook endpoint."""
    id: str
    url: str
    events: List[str]  # event types or "*" for all
    secret: Optional[str] = None  # HMAC secret for signature verification
    retry_policy: str = "exponential"  # linear, exponential
    max_retries: int = 3
    timeout_seconds: float = 10.0
    active: bool = True
    failure_count: int = 0
    last_attempt: Optional[float] = None
    last_success: Optional[float] = None
    last_error: Optional[str] = None


@dataclass
class WebhookDelivery:
    """Record of a delivery attempt."""
    webhook_id: str
    event: str
    payload: Dict[str, Any]
    attempt: int
    delivered: bool
    response_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class WebhookManager:
    """
    Manages webhook registrations and delivers events.
    Persists registrations to disk (in-memory for now; extend to DB).
    """
    
    def __init__(self, http_client: Optional[Any] = None):
        self._hooks: Dict[str, WebhookRegistration] = {}
        self._delivery_log: List[WebhookDelivery] = []
        self._http_client = http_client
        self._lock = asyncio.Lock()
        self._background_tasks: List[asyncio.Task] = []
    
    async def initialize(self):
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not installed; webhook delivery disabled")
            return
        if self._http_client is None:
            import aiohttp
            self._http_client = aiohttp.ClientSession()
        logger.info("Webhook manager initialized")
    
    async def shutdown(self):
        if self._http_client:
            await self._http_client.close()
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Webhook manager shut down")
    
    def register(
        self,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 10.0,
    ) -> str:
        """
        Register a new webhook.
        Returns webhook ID for management.
        """
        hook_id = str(uuid.uuid4())
        reg = WebhookRegistration(
            id=hook_id,
            url=url,
            events=events,
            secret=secret or str(uuid.uuid4()),
            max_retries=max_retries,
            timeout_seconds=timeout,
        )
        self._hooks[hook_id] = reg
        logger.info(f"Webhook registered: {hook_id} → {url} events={events}")
        return hook_id
    
    def unregister(self, hook_id: str) -> bool:
        if hook_id in self._hooks:
            del self._hooks[hook_id]
            logger.info(f"Webhook unregistered: {hook_id}")
            return True
        return False
    
    def list_hooks(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": h.id,
                "url": h.url,
                "events": h.events,
                "active": h.active,
                "failure_count": h.failure_count,
                "last_success": h.last_success,
            }
            for h in self._hooks.values()
        ]
    
    async def deliver(self, event: str, payload: Dict[str, Any]) -> List[str]:
        """
        Deliver event to all matching webhooks.
        Returns list of webhook IDs that accepted delivery.
        """
        delivered = []
        
        # Find matching hooks
        targets = [
            h for h in self._hooks.values()
            if h.active and (event in h.events or "*" in h.events)
        ]
        
        for hook in targets:
            delivery = WebhookDelivery(
                webhook_id=hook.id,
                event=event,
                payload=payload,
                attempt=1,
                delivered=False,
            )
            success = await self._attempt_delivery(hook, delivery)
            if success:
                delivered.append(hook.id)
            else:
                # Schedule retry with backoff
                asyncio.create_task(self._retry_delivery(hook, delivery))
        
        return delivered
    
    async def _attempt_delivery(self, hook: WebhookRegistration, delivery: WebhookDelivery) -> bool:
        if not self._http_client:
            return False
        
        hook.last_attempt = time.time()
        
        try:
            # Sign payload if secret present
            headers = {"Content-Type": "application/json"}
            if hook.secret:
                import hmac, hashlib
                body = json.dumps(payload).encode()
                sig = hmac.new(hook.secret.encode(), body, hashlib.sha256).hexdigest()
                headers["X-Webhook-Signature"] = sig
            
            async with self._http_client.post(
                hook.url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=hook.timeout_seconds),
                headers=headers,
            ) as resp:
                delivery.response_code = resp.status
                delivery.delivered = 200 <= resp.status < 300
                if delivery.delivered:
                    hook.last_success = time.time()
                    hook.failure_count = 0
                else:
                    hook.failure_count += 1
                
                self._log_delivery(delivery)
                return delivery.delivered
        except Exception as e:
            delivery.error = str(e)
            hook.failure_count += 1
            self._log_delivery(delivery)
            return False
    
    async def _retry_delivery(self, hook: WebhookRegistration, initial: WebhookDelivery):
        """Retry with backoff."""
        delay = 1.0
        for attempt in range(2, hook.max_retries + 1):
            await asyncio.sleep(delay)
            
            delivery = WebhookDelivery(
                webhook_id=hook.id,
                event=initial.event,
                payload=initial.payload,
                attempt=attempt,
                delivered=False,
            )
            
            success = await self._attempt_delivery(hook, delivery)
            if success:
                return
            
            if hook.retry_policy == "exponential":
                delay *= 2
            else:
                delay += 2
    
    def _log_delivery(self, delivery: WebhookDelivery):
        self._delivery_log.append(delivery)
        # Keep last 10000
        if len(self._delivery_log) > 10000:
            self._delivery_log = self._delivery_log[-10000:]
    
    def get_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [
            {
                "webhook_id": d.webhook_id,
                "event": d.event,
                "attempt": d.attempt,
                "delivered": d.delivered,
                "error": d.error,
                "ts": d.timestamp,
            }
            for d in self._delivery_log[-limit:]
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        total = len(self._hooks)
        active = sum(1 for h in self._hooks.values() if h.active)
        failed = sum(1 for h in self._hooks.values() if h.failure_count >= h.max_retries)
        return {
            "total": total,
            "active": active,
            "failed": failed,
            "deliveries": len(self._delivery_log),
        }


# Global manager
_global_webhook_mgr: Optional[WebhookManager] = None

def get_webhook_manager() -> WebhookManager:
    global _global_webhook_mgr
    if _global_webhook_mgr is None:
        _global_webhook_mgr = WebhookManager()
    return _global_webhook_mgr


# Hook into existing systems automatically
async def _auto_register_common_webhooks():
    """Register common event hooks if env vars configured."""
    mgr = get_webhook_manager()
    
    # Example: ANOMALY_WEBHOOK_URL env var
    anomaly_url = os.getenv("ANOMALY_WEBHOOK_URL")
    if anomaly_url:
        mgr.register(
            url=anomaly_url,
            events=["anomaly.detected", "sentinel.blocked"],
            secret=os.getenv("ANOMALY_WEBHOOK_SECRET"),
        )
        logger.info("Auto-registered anomaly webhook")
    
    # Chat completion archive
    chat_archive = os.getenv("CHAT_ARCHIVE_WEBHOOK")
    if chat_archive:
        mgr.register(
            url=chat_archive,
            events=["chat.completed"],
            max_retries=5,
        )


# Register routes
@router.post("/register")
async def register_webhook(
    url: str,
    events: List[str],
    secret: Optional[str] = None,
):
    """Register a new webhook endpoint."""
    if not _AIOHTTP_AVAILABLE:
        raise HTTPException(503, "aiohttp not installed; webhooks disabled")
    mgr = get_webhook_manager()
    hook_id = mgr.register(url=url, events=events, secret=secret)
    return {"webhook_id": hook_id, "url": url, "events": events}


@router.delete("/{hook_id}")
async def unregister_webhook(hook_id: str):
    """Unregister a webhook."""
    mgr = get_webhook_manager()
    if mgr.unregister(hook_id):
        return {"ok": True}
    raise HTTPException(404, "Webhook not found")


@router.get("/")
async def list_webhooks():
    """List all registered webhooks."""
    mgr = get_webhook_manager()
    return {"webhooks": mgr.list_hooks()}


@router.get("/stats")
async def webhook_stats():
    mgr = get_webhook_manager()
    return mgr.get_stats()


@router.get("/log")
async def webhook_log(limit: int = 100):
    mgr = get_webhook_manager()
    return {"log": mgr.get_log(limit)}


# Helper for other modules to fire events
async def fire_event(event_type: str, payload: Dict[str, Any]) -> None:
    """
    Fire a system event to all registered webhook listeners.
    Non-blocking — delivery happens in background.
    """
    import os
    mgr = get_webhook_manager()
    # Ensure initialized
    if not mgr._http_client:
        await mgr.initialize()
    
    await mgr.deliver(event_type, {
        "event": event_type,
        "timestamp": time.time(),
        "payload": payload,
    })


__all__ = [
    "WebhookEvent",
    "WebhookRegistration",
    "WebhookManager",
    "get_webhook_manager",
    "fire_event",
    "router",
]

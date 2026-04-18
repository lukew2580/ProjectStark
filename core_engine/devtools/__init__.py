"""
Core Engine — Developer Tools
Enhances DX: debug mode, request/response logging, hot-reload, dev toolbar.
Enabled via DEV_MODE=1 environment variable.
"""

import os
import time
import json
import hashlib
import logging
import asyncio
import threading
from typing import Optional, Dict, Any, List
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import re

logger = logging.getLogger("hardwareless.devtools")

# Global dev mode toggle
DEV_MODE = os.getenv("DEV_MODE", "0") == "1"
DEBUG_MODE = DEV_MODE or os.getenv("DEBUG", "0") == "1"


@dataclass
class RequestLog:
    """Record of an HTTP request for debugging."""
    method: str
    path: str
    headers: Dict[str, str]
    body: str
    client_ip: str
    user_agent: str
    timestamp: float
    duration_ms: Optional[float] = None
    status_code: Optional[int] = None
    response_body_preview: Optional[str] = None
    error: Optional[str] = None


class RequestLogger:
    """
    Middleware-friendly request logger.
    Captures full request/response for inspection; truncates large bodies.
    Thread-safe, async-aware.
    """
    
    MAX_BODY_LOG = 10000  # Max bytes to store per request
    MAX_LOG_ENTRIES = 1000  # Keep last N requests in memory
    
    def __init__(self):
        self._logs: List[RequestLog] = []
        self._lock = threading.Lock()
    
    def create(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: bytes,
        client_ip: str,
        user_agent: str,
    ) -> RequestLog:
        """Create a new log entry."""
        body_str = self._truncate(body.decode('utf-8', errors='replace'))
        log = RequestLog(
            method=method.upper(),
            path=path,
            headers=dict(headers),
            body=body_str,
            client_ip=client_ip,
            user_agent=user_agent,
            timestamp=time.time(),
        )
        with self._lock:
            self._logs.append(log)
            if len(self._logs) > self.MAX_LOG_ENTRIES:
                self._logs.pop(0)
        return log
    
    def complete(
        self,
        log: RequestLog,
        status_code: int,
        response_body: bytes,
        duration_ms: float,
    ) -> None:
        """Mark log entry as completed."""
        log.duration_ms = duration_ms
        log.status_code = status_code
        log.response_body_preview = self._truncate(
            response_body.decode('utf-8', errors='replace')
        )
    
    def error(self, log: RequestLog, exception: Exception) -> None:
        """Mark log entry with error."""
        log.error = str(exception)
    
    def _truncate(self, text: str) -> str:
        if len(text) > self.MAX_BODY_LOG:
            return text[:self.MAX_BODY_LOG] + "...[TRUNCATED]"
        return text
    
    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent logs as dicts."""
        with self._lock:
            recent = self._logs[-limit:][::-1]  # newest first
        return [asdict(l) for l in recent]
    
    def clear(self) -> None:
        with self._lock:
            self._logs.clear()


# Global request logger
_global_reqlog = RequestLogger()
def get_request_logger() -> RequestLogger:
    return _global_reqlog


class DebugModeExtension:
    """
    Adds debug endpoints and behavior when DEBUG_MODE is active.
    - /debug/request-log: view recent HTTP requests
    - /debug/plugins: loaded plugin state
    - /debug/metrics: current metrics
    - /debug/health: detailed health
    - Request body: ?debug=1 query param adds debug info to response
    """
    
    def __init__(self, app):
        self.app = app
        self._enabled = DEBUG_MODE
    
    async def __call__(self, scope, receive, send):
        if not self._enabled:
            await self.app(scope, receive, send)
            return
        
        # Instrument responses: add X-Debug headers
        async def wrapped_send(message):
            if message['type'] == 'http.response.start':
                headers = dict(message.get('headers', []))
                # Decode headers list [b'key', b'value'] to dict
                hdrs = {}
                for k, v in headers.items():
                    hdrs[k.decode()] = v.decode()
                hdrs['X-Debug-Mode'] = 'enabled'
                # Re-encode
                new_headers = [(k.encode(), v.encode()) for k, v in hdrs.items()]
                message['headers'] = new_headers
            await send(message)
        
        await self.app(scope, receive, wrapped_send)


class KnowledgeBaseHotReloader:
    """
    Watches knowledge_preheat.json and reloads encoder on change.
    Uses file mtime polling (simple, no watchdog dependency).
    """
    
    def __init__(self, kb_path: str, reload_callback):
        self.kb_path = Path(kb_path)
        self.reload_callback = reload_callback
        self._last_mtime: Optional[float] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self, poll_interval: float = 2.0):
        self._running = True
        self._task = asyncio.create_task(self._watch_loop(poll_interval))
        logger.info(f"Hot-reload watcher started: {self.kb_path}")
    
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _watch_loop(self, interval: float):
        while self._running:
            try:
                if self.kb_path.exists():
                    mtime = self.kb_path.stat().st_mtime
                    if self._last_mtime is None:
                        self._last_mtime = mtime
                        logger.info(f"Initial KB load detected: {mtime}")
                    elif mtime > self._last_mtime:
                        logger.info(f"KB changed (mtime {mtime}), reloading...")
                        await self.reload_callback()
                        self._last_mtime = mtime
            except Exception as e:
                logger.warning(f"Hot-reload watch error: {e}")
            await asyncio.sleep(interval)
    
    def force_reload(self) -> bool:
        """Manually trigger KB reload. Returns success."""
        try:
            if self.kb_path.exists():
                asyncio.create_task(self.reload_callback())
                return True
        except Exception:
            pass
        return False


# Dev toolbar HTML overlay (injected into HTML responses)
DEV_TOOLBAR_CSS = """
<style>
#hdc-dev-toolbar {
  position: fixed; bottom: 0; right: 0; z-index: 999999;
  background: #1a1a1a; color: #00ff88; font-family: monospace;
  font-size: 11px; padding: 8px 12px; border-top-left-radius: 6px;
  box-shadow: -2px -2px 8px rgba(0,0,0,0.3);
}
#hdc-dev-toolbar .stat { margin: 2px 0; }
#hdc-dev-toolbar .key { color: #00aaff; }
#hdc-dev-toolbar .val { color: #ffcc00; }
</style>
"""

DEV_TOOLBAR_HTML = """
<div id="hdc-dev-toolbar">
  <div class="stat"><span class="key">Mode:</span> <span class="val" id="hdc-mode">DEV</span></div>
  <div class="stat"><span class="key">Routes:</span> <span class="val" id="hdc-routes">--</span></div>
  <div class="stat"><span class="key">Plugins:</span> <span class="val" id="hdc-plugins">--</span></div>
  <div class="stat"><span class="key">Cache:</span> <span class="val" id="hdc-cache">--</span></div>
</div>
<script>
(async () => {
  const fetchStats = async () => {
    try {
      const r = await fetch('/debug/stats');
      const j = await r.json();
      document.getElementById('hdc-routes').textContent = j.routes || '--';
      document.getElementById('hdc-plugins').textContent = j.active_plugins + '/' + j.total_plugins;
      document.getElementById('hdc-cache').textContent = j.cache_hit_rate || '--';
    } catch(e) {}
  };
  fetchStats();
  setInterval(fetchStats, 2000);
})();
</script>
"""


class DevToolbarMiddleware:
    """
    Injects dev toolbar overlay into HTML responses in debug mode.
    Only applies to text/html responses (SPA pages).
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if not DEBUG_MODE:
            await self.app(scope, receive, send)
            return
        
        async def wrapped_send(message):
            if message['type'] == 'http.response.start':
                headers = dict(message.get('headers', []))
                content_type = headers.get(b'content-type', b'').decode()
                if 'text/html' in content_type:
                    # Mark for body injector
                    message['hdc-inject-toolbar'] = True
            elif message['type'] == 'http.response.body':
                # Inject toolbar HTML if marked
                if message.get('hdc-inject-toolbar'):
                    body = message.get('body', b'')
                    if body:
                        try:
                            html = body.decode('utf-8')
                            if '</body>' in html:
                                toolbar = DEV_TOOLBAR_CSS + DEV_TOOLBAR_HTML
                                html = html.replace('</body>', toolbar + '</body>')
                                message['body'] = html.encode('utf-8')
                        except Exception:
                            pass  # ignore decode errors
                # Remove marker
                message.pop('hdc-inject-toolbar', None)
            await send(message)
        
        await self.app(scope, receive, wrapped_send)


# Hot-reload KB helper
def create_kb_reloader(encoder, decoder, knowledge_base_path: str):
    """
    Create a callback that reloads the knowledge base preheat.
    """
    async def reload_knowledge():
        try:
            import json
            kb_path = Path(knowledge_base_path)
            if kb_path.exists():
                with open(kb_path, "r") as f:
                    dna = json.load(f)
                # Assuming encoder has bulk_ingest
                if hasattr(encoder, 'bulk_ingest'):
                    count = encoder.bulk_ingest(dna)
                    logger.info(f"Reloaded KB: {count} concepts")
                else:
                    logger.warning("Encoder has no bulk_ingest method")
        except Exception as e:
            logger.error(f"KB reload failed: {e}")
    
    return reload_knowledge


__all__ = [
    "DEV_MODE",
    "DEBUG_MODE",
    "RequestLog",
    "RequestLogger",
    "get_request_logger",
    "DebugModeExtension",
    "KnowledgeBaseHotReloader",
    "create_kb_reloader",
    "DevToolbarMiddleware",
]

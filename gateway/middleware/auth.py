"""
Hardwareless AI — Gateway Middleware
Enhanced authentication, rate limiting, validation, and security.
"""
import time
import secrets
import hashlib
import json
import logging
import os
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Import security modules
from core_engine.security.validator import (
    get_validator,
    get_audit_logger,
    get_anomaly_detector,
    get_request_signer,
    RequestSigner,
)


class RateLimitExceeded(Exception):
    """Rate limit exceeded exception."""
    pass


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, requests: int = 100, window_seconds: int = 60):
        self.requests = requests
        self.window = window_seconds
        self._buckets: Dict[str, list] = {}
    
    def check(self, client_id: str) -> bool:
        """Check if client is within rate limit."""
        now = time.time()
        window_start = now - self.window
        
        if client_id not in self._buckets:
            self._buckets[client_id] = []
        
        bucket = self._buckets[client_id]
        bucket[:] = [t for t in bucket if t > window_start]
        
        if len(bucket) >= self.requests:
            return False
        
        bucket.append(now)
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        now = time.time()
        window_start = now - self.window
        
        bucket = self._buckets.get(client_id, [])
        recent = [t for t in bucket if t > window_start]
        
        return max(0, self.requests - len(recent))
    
    def reset(self, client_id: str):
        """Reset rate limit for client."""
        if client_id in self._buckets:
            del self._buckets[client_id]


class APIKeyManager:
    """API key management."""
    
    def __init__(self):
        self._keys: Dict[str, Dict] = {}
        self._default_key = self._create_default_key()
    
    def _hash_key(self, key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def _create_default_key(self) -> str:
        """Create default development key."""
        default_key = "hw_dev_" + secrets.token_hex(16)
        hashed = self._hash_key(default_key)
        self._keys[hashed] = {
            "key": default_key,
            "name": "default",
            "rate_limit": 100,
            "scopes": ["read", "write"],
            "created_at": time.time()
        }
        return default_key
    
    def create_key(self, name: str, rate_limit: int = 100, scopes: Optional[list] = None) -> str:
        """Create new API key."""
        key = "hw_" + secrets.token_hex(16)
        hashed = self._hash_key(key)
        
        self._keys[hashed] = {
            "key": key,
            "name": name,
            "rate_limit": rate_limit,
            "scopes": scopes or ["read"],
            "created_at": time.time()
        }
        return key
    
    def verify_key(self, key: str) -> Optional[Dict]:
        """Verify API key."""
        if not key:
            return None
        
        if key.startswith("hw_"):
            hashed = self._hash_key(key)
            return self._keys.get(hashed)
        
        if key == self._default_key:
            return self._keys.get(self._hash_key(self._default_key))
        
        return None
    
    def revoke_key(self, key: str) -> bool:
        """Revoke API key."""
        hashed = self._hash_key(key)
        if hashed in self._keys:
            del self._keys[hashed]
            return True
        return False
    
    def list_keys(self) -> list:
        """List all API keys (without secrets)."""
        return [
            {"name": v["name"], "scopes": v["scopes"], "rate_limit": v["rate_limit"]}
            for v in self._keys.values()
        ]


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware."""
    
    def __init__(self, app, api_key_manager: Optional[APIKeyManager] = None):
        super().__init__(app)
        self.key_manager = api_key_manager or APIKeyManager()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with authentication."""
        path = request.url.path
        
        if path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        api_key = request.headers.get("x-api-key")
        
        if api_key:
            key_info = self.key_manager.verify_key(api_key)
            if key_info:
                request.state.api_key = key_info
                return await call_next(request)
        
        request.state.api_key = None
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(self, app, limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or RateLimiter()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        path = request.url.path
        
        if path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        client_id = request.client.host if request.client else "unknown"
        
        if not self.limiter.check(client_id):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
        
        request.state.rate_limit_remaining = self.limiter.get_remaining(client_id)
        return await call_next(request)


_global_limiter: Optional[RateLimiter] = None
_global_key_manager: Optional[APIKeyManager] = None


def get_rate_limiter() -> RateLimiter:
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter


def get_api_key_manager() -> APIKeyManager:
    global _global_key_manager
    if _global_key_manager is None:
        _global_key_manager = APIKeyManager()
    return _global_key_manager


class RequestSignatureMiddleware(BaseHTTPMiddleware):
    """Verifies HMAC request signatures to prevent replay attacks."""
    
    def __init__(self, app, signer: Optional[RequestSigner] = None):
        super().__init__(app)
        self.signer = signer or get_request_signer()
    
    async def dispatch(self, request: Request, call_next):
        """Verify request signature if enabled."""
        # Skip signature check for health/docs and if not enabled via env
        if not os.getenv("ENABLE_REQUEST_SIGNING"):
            return await call_next(request)
        
        path = request.url.path
        if path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        signature = request.headers.get("X-Signature")
        if not signature:
            raise HTTPException(status_code=401, detail="Missing request signature")
        
        # Build payload from request method, path, body
        try:
            body = await request.body()
            body_json = json.loads(body) if body else {}
        except Exception:
            body_json = {}
        
        payload = {
            "method": request.method,
            "path": str(request.url.path),
            "body": body_json,
        }
        
        if not self.signer.verify_request(payload, signature):
            audit = get_audit_logger()
            audit.log_auth_failure(
                client_ip=request.client.host if request.client else "unknown",
                reason="Invalid or replayed signature",
                user_agent=request.headers.get("user-agent")
            )
            raise HTTPException(status_code=401, detail="Invalid request signature")
        
        return await call_next(request)

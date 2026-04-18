"""
Core Engine — Advanced Security
CSRF protection, bot detection/fingerprinting, PII redaction, secrets vault.
Extends the existing validator system.
"""

import re
import os
import time
import uuid
import hashlib
import hmac
import secrets
import logging
import asyncio
from typing import Dict, Optional, List, Any, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("hardwareless.security.advanced")

# Lazy imports for optional deps (aiohttp, hvac, aioboto3, sse-starlette are optional)


# ——————————————————————————————
# CSRF Protection
# ——————————————————————————————

class CSRFToken:
    """
    Double-submit cookie CSRF token.
    Clients must echo token from cookie to header/query.
    """
    
    def __init__(self, secret: Optional[str] = None):
        self.secret = (secret or secrets.token_hex(32)).encode()
        self._cookie_name = "hdc_csrf"
        self._header_name = "X-CSRF-Token"
    
    def generate(self, session_id: str) -> str:
        """Create CSRF token tied to session."""
        data = f"{session_id}:{time.time()}".encode()
        sig = hmac.new(self.secret, data, hashlib.sha256).hexdigest()[:16]
        return f"{session_id}-{sig}"
    
    def verify(self, token: str, session_id: str) -> bool:
        """Verify token matches session."""
        try:
            parts = token.split("-")
            if len(parts) != 2:
                return False
            token_session, token_sig = parts
            if token_session != session_id:
                return False
            expected = hmac.new(
                self.secret,
                f"{session_id}:{time.time()}".encode(),
                hashlib.sha256,
            ).hexdigest()[:16]
            return hmac.compare_digest(token_sig, expected[:16])
        except Exception:
            return False
    
    def set_cookie_headers(self, token: str) -> Dict[str, str]:
        return {
            "Set-Cookie": f"{self._cookie_name}={token}; Path=/; HttpOnly; SameSite=Lax",
        }


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Enforces CSRF checks for state-changing requests (POST/PUT/DELETE/PATCH).
    Skips for safe methods and configured endpoints.
    """
    
    def __init__(
        self,
        app,
        cookie_name: str = "hdc_csrf",
        header_name: str = "X-CSRF-Token",
        exempt_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/openapi.json", "/v1/chat/completions", "/batch"]
    
    async def dispatch(self, request: Request, call_next):
        # Only check unsafe methods
        if request.method.upper() in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return await call_next(request)
        
        path = request.url.path
        if any(path.startswith(p) for p in self.exempt_paths):
            return await call_next(request)
        
        # Get token from header
        token = request.headers.get(self.header_name)
        if not token:
            raise HTTPException(status_code=403, detail="CSRF token missing")
        
        # Get session ID from cookie
        session_cookie = request.cookies.get(self.cookie_name)
        if not session_cookie:
            raise HTTPException(status_code=403, detail="CSRF session cookie missing")
        
        # Verify
        csrf = CSRFToken()
        if not csrf.verify(token, session_cookie):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
        
        return await call_next(request)


# ——————————————————————————————
# Bot Detection & Fingerprinting
# ——————————————————————————————

@dataclass
class Fingerprint:
    """Browser/client fingerprint for bot scoring."""
    user_agent: str
    ip: str
    headers_fingerprint: str
    timing_score: float = 0.0
    mouse_movement: Optional[float] = None
    tls_version: Optional[str] = None
    ja3_hash: Optional[str] = None
    risk_score: float = 0.0  # 0 (safe) to 1 (high risk)


class BotScorer:
    """
    Assigns risk scores based on fingerprint characteristics.
    """
    
    # Known bot signatures
    BOT_UAS = [
        "bot", "spider", "crawl", "scrape", "headless", "python-requests",
        "curl", "wget", "httpie", "postman", "insomnia", "java", "okhttp",
    ]
    
    SUSPICIOUS_HEADERS = [
        "X-Forwarded-Host", "X-Forwarded-Server", "Via",
    ]
    
    @classmethod
    def score(cls, fp: Fingerprint) -> float:
        """Calculate risk score 0–1."""
        score = 0.0
        
        # UA analysis
        ua_lower = fp.user_agent.lower()
        if any(token in ua_lower for token in cls.BOT_UAS):
            score += 0.4
        
        # Missing common browser headers
        if "accept-language" not in fp.headers_fingerprint.lower():
            score += 0.2
        
        # Timing: too fast/fast navigation could indicate script
        if fp.timing_score > 0.9:
            score += 0.2
        
        # No mouse movement? (not tracked, but placeholder)
        if fp.mouse_movement is None:
            score += 0.1
        
        return min(score, 1.0)
    
    @classmethod
    def is_bot(cls, fp: Fingerprint, threshold: float = 0.6) -> bool:
        return cls.score(fp) >= threshold


class FingerprintMiddleware(BaseHTTPMiddleware):
    """
    Extracts and scores client fingerprint on every request.
    Adds X-Client-Risk header; can optionally block high-risk clients.
    """
    
    def __init__(self, app, block_threshold: float = 0.8):
        super().__init__(app)
        self.block_threshold = block_threshold
    
    async def dispatch(self, request: Request, call_next):
        # Build fingerprint
        ua = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else "unknown"
        hdrs = str(sorted(request.headers.keys()))
        timing = request.headers.get("Sec-CH-UA", "")  # client hints
        
        fp = Fingerprint(
            user_agent=ua,
            ip=client_ip,
            headers_fingerprint=hdrs,
            timing_score=0.0,  # TODO: parse timing headers
        )
        
        risk = BotScorer.score(fp)
        
        # Block extremely risky
        if risk >= self.block_threshold:
            logger.warning(f"Blocked high-risk client: ip={client_ip} risk={risk:.2f} UA={ua[:50]}")
            raise HTTPException(status_code=403, detail="Suspicious request blocked")
        
        # Attach score to request state
        request.state.client_risk = risk
        
        response = await call_next(request)
        response.headers["X-Client-Risk"] = f"{risk:.2f}"
        return response


# ——————————————————————————————
# PII Redaction
# ——————————————————————————————

class PIIRedactor:
    """
    Redacts personally identifiable information from logs and outputs.
    Uses regex patterns for common PII: emails, phones, SSNs, credit cards, etc.
    """
    
    PATTERNS = {
        "email": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        "phone_us": re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        "credit_card": re.compile(r'\b(?:\d{4}[- ]?){3}\d{4}\b'),
        "ip_address": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        "uuid": re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'),
    }
    
    REDACTION_MAP = {
        "email": "[EMAIL REDACTED]",
        "phone_us": "[PHONE REDACTED]",
        "ssn": "[SSN REDACTED]",
        "credit_card": "[CARD REDACTED]",
        "ip_address": "[IP REDACTED]",
        "uuid": "[UUID REDACTED]",
    }
    
    @classmethod
    def redact(cls, text: str) -> str:
        """Redact all PII from text."""
        result = text
        for pii_type, pattern in cls.PATTERNS.items():
            replacement = cls.REDACTION_MAP[pii_type]
            result = pattern.sub(replacement, result)
        return result
    
    @classmethod
    def redact_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact PII from dict values."""
        def visit(obj):
            if isinstance(obj, str):
                return cls.redact(obj)
            if isinstance(obj, dict):
                return {k: visit(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [visit(i) for i in obj]
            return obj
        return visit(data)


# ——————————————————————————————
# Secrets Vault Integration (HashiCorp Vault / AWS Secrets Manager)
# ——————————————————————————————

class SecretsVault:
    """
    Abstract secrets backend. Implementations: Vault, AWS, Env File.
    Used for API keys, signing secrets, DB passwords.
    """
    
    async def get(self, key: str) -> Optional[str]:
        raise NotImplementedError
    
    async def set(self, key: str, value: str) -> bool:
        raise NotImplementedError
    
    async def delete(self, key: str) -> bool:
        raise NotImplementedError
    
    async def list(self) -> List[str]:
        raise NotImplementedError


class EnvFileVault(SecretsVault):
    """
    .env file backend. Serves as fallback/development vault.
    """
    
    def __init__(self, env_path: str = ".env"):
        self.env_path = env_path
        self._cache: Dict[str, str] = {}
        self._load()
    
    def _load(self):
        import dotenv
        try:
            from dotenv import load_dotenv
            load_dotenv(self.env_path)
        except ImportError:
            pass
    
    async def get(self, key: str) -> Optional[str]:
        return os.getenv(key)
    
    async def set(self, key: str, value: str) -> bool:
        # Can't persist back to .env easily
        return False
    
    async def delete(self, key: str) -> bool:
        return False
    
    async def list(self) -> List[str]:
        return []


class HashiCorpVault(SecretsVault):
    """
    HashiCorp Vault backend (requires hvac).
    Uses AppRole or token auth depending on config.
    """
    
    def __init__(
        self,
        vault_url: str,
        token: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        mount_point: str = "secret",
    ):
        self.vault_url = vault_url.rstrip("/")
        self.token = token
        self.role_id = role_id
        self.secret_id = secret_id
        self.mount_point = mount_point
        self._client = None
    
    async def initialize(self):
        try:
            import hvac
        except ImportError:
            raise RuntimeError("hvac library required for Vault backend")
        
        self._client = hvac.AsyncClient(url=self.vault_url)
        
        if self.token:
            self._client.token = self.token
        elif self.role_id and self.secret_id:
            login_resp = await self._client.auth_approle(
                role_id=self.role_id,
                secret_id=self.secret_id,
            )
            self._client.token = login_resp["auth"]["client_token"]
        else:
            raise ValueError("Vault requires token or AppRole credentials")
        
        logger.info("HashiCorp Vault client initialized")
    
    async def get(self, key: str) -> Optional[str]:
        if not self._client:
            await self.initialize()
        try:
            secret = await self._client.secrets.kv.v2.read_secret_version(
                path=key,
                mount_point=self.mount_point,
            )
            return secret["data"]["data"].get("value")
        except Exception as e:
            logger.error(f"Vault get error: {e}")
            return None
    
    async def set(self, key: str, value: str) -> bool:
        if not self._client:
            await self.initialize()
        try:
            await self._client.secrets.kv.v2.create_or_update_secret(
                path=key,
                secret={"value": value},
                mount_point=self.mount_point,
            )
            return True
        except Exception as e:
            logger.error(f"Vault set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        if not self._client:
            await self.initialize()
        try:
            await self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=key,
                mount_point=self.mount_point,
            )
            return True
        except Exception:
            return False
    
    async def list(self) -> List[str]:
        if not self._client:
            await self.initialize()
        try:
            secrets = await self._client.secrets.kv.v2.list_secrets(
                mount_point=self.mount_point,
            )
            return secrets["data"]["keys"]
        except Exception:
            return []


class AWSSecretsManagerBackend(SecretsVault):
    """
    AWS Secrets Manager backend.
    """
    
    def __init__(self, region: str = "us-east-1", profile: Optional[str] = None):
        self.region = region
        self.profile = profile
        self._client = None
    
    async def initialize(self):
        try:
            import aioboto3
        except ImportError:
            raise RuntimeError("aioboto3 required for AWS Secrets Manager")
        
        session_kwargs = {"region_name": self.region}
        if self.profile:
            session_kwargs["profile_name"] = self.profile
        
        session = aioboto3.Session(**session_kwargs)
        self._client = await session.client("secretsmanager").__aenter__()
        logger.info("AWS Secrets Manager client initialized")
    
    async def get(self, key: str) -> Optional[str]:
        if not self._client:
            await self.initialize()
        try:
            resp = await self._client.get_secret_value(SecretId=key)
            return resp["SecretString"]
        except self._client.exceptions.ResourceNotFoundException:
            return None
        except Exception as e:
            logger.error(f"AWS SM get error: {e}")
            return None
    
    async def set(self, key: str, value: str) -> bool:
        if not self._client:
            await self.initialize()
        try:
            await self._client.put_secret_value(
                SecretId=key,
                SecretString=value,
            )
            return True
        except Exception as e:
            logger.error(f"AWS SM set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        if not self._client:
            await self.initialize()
        try:
            await self._client.delete_secret(SecretId=key, ForceDeleteWithoutRecovery=True)
            return True
        except Exception:
            return False
    
    async def list(self) -> List[str]:
        if not self._client:
            await self.initialize()
        try:
            paginator = self._client.get_paginator("list_secrets")
            keys = []
            async for page in paginator.paginate():
                for secret in page["SecretList"]:
                    keys.append(secret["Name"])
            return keys
        except Exception:
            return []


# ——————————————————————————————
# Threat Intelligence Feed Integration
# ——————————————————————————————

class ThreatFeed:
    """External threat intelligence source (malicious IPs,UserAgents, patterns)."""
    
    def __init__(self, url: str, update_interval_seconds: float = 3600):
        self.url = url
        self.update_interval = update_interval_seconds
        self._last_update: float = 0
        self._threat_ips: Set[str] = set()
        self._threat_uas: Set[str] = set()
        self._lock = asyncio.Lock()
    
    async def update(self) -> None:
        """Fetch latest threat data from feed."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Parse threat indicators (format depends on feed)
                        self._threat_ips = set(data.get("ips", []))
                        self._threat_uas = set(data.get("user_agents", []))
                        self._last_update = time.time()
                        logger.info(f"Threat feed updated: {len(self._threat_ips)} IPs, {len(self._threat_uas)} UAs")
        except Exception as e:
            logger.error(f"Threat feed update failed: {e}")
    
    def is_malicious_ip(self, ip: str) -> bool:
        return ip in self._threat_ips
    
    def is_malicious_ua(self, ua: str) -> bool:
        return any(t in ua for t in self._threat_uas)
    
    async def start_periodic_update(self):
        """Background task to refresh feed."""
        while True:
            await asyncio.sleep(self.update_interval)
            await self.update()


# Global threat feed manager
_threat_feeds: List[ThreatFeed] = []


async def load_threat_feeds():
    """Initialize threat feeds from env var."""
    import os
    feeds_url = os.getenv("THREAT_FEED_URLS")
    if feeds_url:
        for url in feeds_url.split(","):
            feed = ThreatFeed(url.strip())
            await feed.update()
            _threat_feeds.append(feed)
            asyncio.create_task(feed.start_periodic_update())
            logger.info(f"Loaded threat feed: {url}")


__all__ = [
    "CSRFToken",
    "CSRFMiddleware",
    "Fingerprint",
    "BotScorer",
    "FingerprintMiddleware",
    "PIIRedactor",
    "SecretsVault",
    "EnvFileVault",
    "HashiCorpVault",
    "AWSSecretsManagerBackend",
    "ThreatFeed",
    "load_threat_feeds",
]

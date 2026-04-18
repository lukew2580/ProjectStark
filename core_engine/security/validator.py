"""
Hardwareless AI — Security Enhancement Module

Adds layered defenses:
1. Input validation & sanitization
2. Request signing & replay protection
3. Audit logging
4. Anomaly detection
5. Secure headers
"""
import time
import hashlib
import hmac
import secrets
import json
import re
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging

# Configure audit logger
audit_logger = logging.getLogger("hardwareless.security")
audit_logger.setLevel(logging.INFO)

class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security incident record."""
    timestamp: str
    level: SecurityLevel
    event_type: str
    client_ip: str
    user_agent: Optional[str]
    details: Dict[str, Any]
    session_id: Optional[str] = None


class InputValidator:
    """Validates and sanitizes user inputs."""
    
    # Maximum lengths for different input types
    MAX_QUESTION_LENGTH = 1000
    MAX_MESSAGE_LENGTH = 5000
    MAX_VECTOR_SAMPLES = 1000
    
    # Dangerous patterns (basic XSS/injection prevention)
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=\s*["\']',
        r'<iframe[^>]*>',
        r'eval\s*\(',
        r'document\.cookie',
        r'\.innerHTML',
    ]
    
    @classmethod
    def validate_question(cls, question: str) -> tuple[bool, Optional[str]]:
        """Validate chat question."""
        if not question or not question.strip():
            return False, "Question cannot be empty"
        
        if len(question) > cls.MAX_QUESTION_LENGTH:
            return False, f"Question too long (max {cls.MAX_QUESTION_LENGTH} chars)"
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, question, re.IGNORECASE):
                return False, "Input contains potentially dangerous content"
        
        return True, None
    
    @classmethod
    def validate_translation_text(cls, text: str) -> tuple[bool, Optional[str]]:
        """Validate translation input."""
        if not text or len(text.strip()) < 1:
            return False, "Text cannot be empty"
        
        if len(text) > cls.MAX_MESSAGE_LENGTH:
            return False, f"Text too long (max {cls.MAX_MESSAGE_LENGTH} chars)"
        
        # Same pattern checks
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "Input contains potentially dangerous content"
        
        return True, None
    
    @classmethod
    def sanitize(cls, text: str) -> str:
        """Basic sanitization: strip dangerous constructs."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove script-like patterns
        text = re.sub(r'script|javascript|eval\(|document\.', '', text, flags=re.IGNORECASE)
        return text.strip()


class RequestSigner:
    """
    Request signing to prevent replay attacks.
    Uses HMAC-SHA256 with timestamp nonce.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret = (secret_key or secrets.token_hex(32)).encode()
        self.nonce_store: Dict[str, float] = {}  # For replay protection
        self.nonce_ttl = 60.0  # Seconds to remember nonces
    
    def sign_request(self, payload: Dict[str, Any], timestamp: Optional[float] = None) -> str:
        """Generate HMAC signature for request."""
        ts = timestamp or time.time()
        payload_str = json.dumps(payload, sort_keys=True)
        message = f"{ts}.{payload_str}".encode()
        signature = hmac.new(self.secret, message, hashlib.sha256).hexdigest()
        return f"{ts}.{signature}"
    
    def verify_request(self, payload: Dict[str, Any], signature: str, tolerance: float = 30.0) -> bool:
        """Verify request signature and check replay."""
        try:
            ts_str, sig = signature.split('.', 1)
            ts = float(ts_str)
        except (ValueError, AttributeError):
            return False
        
        # Check timestamp freshness (prevent old replay)
        now = time.time()
        if abs(now - ts) > tolerance:
            return False
        
        # Check for replay (same request seen before)
        nonce = f"{ts}:{sig[:16]}"  # Use prefix as nonce
        if nonce in self.nonce_store:
            return False
        
        # Store nonce (with cleanup)
        self.nonce_store[nonce] = now
        self._cleanup_old_nonces()
        
        # Verify HMAC
        payload_str = json.dumps(payload, sort_keys=True)
        message = f"{ts}.{payload_str}".encode()
        expected = hmac.new(self.secret, message, hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(sig, expected)
    
    def _cleanup_old_nonces(self):
        """Remove expired nonces."""
        now = time.time()
        cutoff = now - self.nonce_ttl
        expired = [k for k, v in self.nonce_store.items() if v < cutoff]
        for k in expired:
            del self.nonce_store[k]


class AuditLogger:
    """
    Centralized audit logging for security events.
    """
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.event_count = 0  # Track total events
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            audit_logger.addHandler(handler)
    
    def log_event(self, event: SecurityEvent):
        """Log a security event."""
        audit_logger.warning(
            f"[{event.level.value.upper()}] {event.event_type} | "
            f"IP={event.client_ip} UA={event.user_agent or 'unknown'} | "
            f"details={json.dumps(event.details)}"
        )
        self.event_count += 1
    
    def log_auth_failure(self, client_ip: str, reason: str, user_agent: Optional[str] = None):
        """Log authentication failure."""
        self.log_event(SecurityEvent(
            timestamp=datetime.utcnow().isoformat(),
            level=SecurityLevel.MEDIUM,
            event_type="auth_failure",
            client_ip=client_ip,
            user_agent=user_agent,
            details={"reason": reason}
        ))
    
    def log_rate_limit(self, client_ip: str, limit_type: str):
        """Log rate limit trigger."""
        self.log_event(SecurityEvent(
            timestamp=datetime.utcnow().isoformat(),
            level=SecurityLevel.LOW,
            event_type="rate_limit",
            client_ip=client_ip,
            user_agent=None,
            details={"limit": limit_type}
        ))
    
    def log_suspicious_payload(self, client_ip: str, payload: Dict, reason: str):
        """Log suspicious request payload."""
        self.log_event(SecurityEvent(
            timestamp=datetime.utcnow().isoformat(),
            level=SecurityLevel.HIGH,
            event_type="suspicious_payload",
            client_ip=client_ip,
            user_agent=None,
            details={"reason": reason, "payload_keys": list(payload.keys())}
        ))


class AnomalyDetector:
    """
    Simple statistical anomaly detection for request patterns.
    """
    
    def __init__(self, window_size: int = 100, z_threshold: float = 3.0):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.request_times: List[float] = []
        self.request_sizes: List[int] = []
        self.anomaly_count = 0  # Track total anomalies detected
    
    def record_request(self, size_bytes: int):
        """Record a request for anomaly analysis."""
        now = time.time()
        self.request_times.append(now)
        self.request_sizes.append(size_bytes)
        
        # Trim old data
        cutoff = now - 60.0  # 1-minute window
        while self.request_times and self.request_times[0] < cutoff:
            self.request_times.pop(0)
            self.request_sizes.pop(0)
    
    def check_anomaly(self, current_size: int) -> Optional[str]:
        """Check if current request is anomalous."""
        if len(self.request_sizes) < 10:
            return None  # Not enough data
        
        mean_size = sum(self.request_sizes) / len(self.request_sizes)
        std_size = (sum((s - mean_size) ** 2 for s in self.request_sizes) / len(self.request_sizes)) ** 0.5
        
        if std_size == 0:
            return None
        
        z_score = abs(current_size - mean_size) / std_size
        
        if z_score > self.z_threshold:
            self.anomaly_count += 1
            return f"Request size anomaly detected (z={z_score:.2f})"
        
        return None


# Global instances (initialized on startup)
_global_validator = InputValidator()
_global_audit = AuditLogger()
_global_detector = AnomalyDetector()
_global_signer: Optional[RequestSigner] = None


def get_validator() -> InputValidator:
    return _global_validator


def get_audit_logger() -> AuditLogger:
    return _global_audit


def get_anomaly_detector() -> AnomalyDetector:
    return _global_detector


def get_request_signer() -> RequestSigner:
    """Get or create the global request signer."""
    global _global_signer
    if _global_signer is None:
        import os
        secret = os.getenv("REQUEST_SIGNING_SECRET")
        _global_signer = RequestSigner(secret_key=secret)
    return _global_signer

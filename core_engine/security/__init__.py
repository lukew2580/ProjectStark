"""
Core Engine — Security Package
Exposes security utilities for gateway and internal use.
Backward-compatible aliases for legacy code.
"""

from .validator import (
    InputValidator,
    RequestSigner,
    AuditLogger,
    AnomalyDetector,
    SecurityLevel,
    SecurityEvent,
    get_validator,
    get_audit_logger,
    get_anomaly_detector,
    get_request_signer,
)

# Backward compatibility: legacy names used in older tests/docs
ThreatLevel = SecurityLevel
get_security = get_validator  # legacy alias

__all__ = [
    "InputValidator",
    "RequestSigner",
    "AuditLogger",
    "AnomalyDetector",
    "SecurityLevel",
    "ThreatLevel",  # legacy alias
    "SecurityEvent",
    "get_validator",
    "get_audit_logger",
    "get_anomaly_detector",
    "get_request_signer",
    "get_security",  # legacy alias
]

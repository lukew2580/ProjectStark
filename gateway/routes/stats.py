"""
Hardwareless AI — Swarm Statistics
"""
import time
from fastapi import APIRouter

router = APIRouter()

# Mock stats for initial "beef-up" dashboard
# In a full deployment, these would track packet sizes from HypervectorServer
START_TIME = time.time()

# Import security metrics
from core_engine.security.validator import get_audit_logger, get_anomaly_detector

_audit = get_audit_logger()
_detector = get_anomaly_detector()


@router.get("/v1/stats")
async def get_stats():
    """Returns rolling swarm metrics for the Mission Control dashboard."""
    uptime = time.time() - START_TIME
    
    return {
        "uptime_seconds": int(uptime),
        "total_packets_processed": int(uptime * 1.5),  # Simulated load
        "avg_node_latency_ms": 12.5,
        "bandwidth_kbps": 45.3,
        "swarm_stability": 99.98,
        # Security metrics
        "security": {
            "audit_events_total": getattr(_audit, "event_count", 0),
            "anomalies_detected": getattr(_detector, "anomaly_count", 0),
            "active_anomaly_window": len(_detector.request_sizes),
        }
    }

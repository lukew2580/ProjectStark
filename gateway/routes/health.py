"""
Hardwareless AI — Health & Swarm Monitoring
"""
import time
from fastapi import APIRouter
from config.settings import DIMENSIONS, KNOWLEDGE_BASE, DEFAULT_NODE_COUNT

router = APIRouter()

# Global reference to the swarm server (optional, injected on boot)
swarm_server = None

@router.get("/health")
async def health():
    """Detailed health check with real-time swarm diagnostics and links."""
    global swarm_server
    
    swarm_data = {}
    if swarm_server:
        swarm_data = swarm_server.get_swarm_health()
    
    # Discovery Links for Mobile Nodes (Swift/Kotlin)
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"

    return {
        "status": "operational",
        "engine": "Hardwareless HDC v3 + LeanCTX",
        "discovery_links": {
            "gateway": f"http://{local_ip}:8000",
            "swarm_server": f"tcp://{local_ip}:8888"
        },
        "swarm_vitality": {
            "active_nodes": len(swarm_data),
            "node_registry": swarm_data
        },
        "diagnostics": {
            "dimensions": DIMENSIONS,
            "kb_size": len(KNOWLEDGE_BASE),
            "pipeline_depth": DEFAULT_NODE_COUNT
        }
    }

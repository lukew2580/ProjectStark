"""
Hardwareless AI — Bridge API Routes
Universal platform bridge endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/bridge", tags=["bridge"])


class ConnectRequest(BaseModel):
    host: str
    port: int = 8888


class SendToNodeRequest(BaseModel):
    node_id: int
    vector_data: str  # Base64 encoded


class BroadcastRequest(BaseModel):
    vector_data: str  # Base64 encoded
    platform: Optional[str] = None  # python, kotlin, swift, js, rust


@router.get("/status")
async def get_bridge_status():
    """Get bridge status and connected nodes."""
    from core_engine.bridge import get_bridge
    
    bridge = get_bridge()
    return {
        "connected_nodes": bridge.get_connected_nodes(),
        "platform_stats": bridge.get_platform_stats(),
        "note": "Hardwareless AI - True CPU/GPU-less platform bridge"
    }


@router.get("/nodes")
async def list_nodes():
    """List all connected nodes across platforms."""
    from core_engine.bridge import get_bridge
    
    bridge = get_bridge()
    return {"nodes": bridge.get_connected_nodes()}


@router.post("/connect")
async def connect_to_node(request: ConnectRequest):
    """Connect to another bridge node."""
    from core_engine.bridge import get_bridge
    
    bridge = get_bridge()
    try:
        client = await bridge.connect_to(request.host, request.port)
        return {
            "status": "connected",
            "host": request.host,
            "port": request.port
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/platforms")
async def list_platforms():
    """List supported platforms."""
    from core_engine.bridge import Platform
    
    return {
        "platforms": [
            {"id": p.value, "name": p.name, "runtime": _get_runtime(p)}
            for p in Platform
        ],
        "note": "Hardwareless AI - No CPU/GPU required on any platform"
    }


def _get_runtime(platform) -> str:
    runtimes = {
        "PYTHON": "Python 3.10+ (pure HDC)",
        "KOTLIN": "Kotlin/JVM (Android native)",
        "SWIFT": "Swift 5+ (iOS native)", 
        "JAVASCRIPT": "Node.js/Browser",
        "RUST": "Rust (Desktop)"
    }
    return runtimes.get(platform.name, "Unknown")


@router.get("/protocol")
async def get_protocol_info():
    """Get HV01 protocol information."""
    return {
        "protocol": "HV01",
        "version": 2,
        "header_size": 43,
        "vector_dimensions": 10000,
        "flags": {
            "encrypted": 0x01,
            "heartbeat": 0x02
        },
        "note": "True hardwareless - element-wise binary operations only"
    }
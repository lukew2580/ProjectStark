"""
Hardwareless AI — XR/VR API Routes
Connect to VR/AR glasses and headsets
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/xr", tags=["xr"])


class ConnectPlatformRequest(BaseModel):
    platform: str  # openxr, meta_rayban, xg_glass, steamvr
    config: Optional[Dict[str, Any]] = {}


class SendDisplayRequest(BaseModel):
    device_id: str
    content: str


@router.get("/platforms")
async def list_xr_platforms():
    """List supported XR platforms."""
    return {
        "platforms": [
            {"id": "openxr", "name": "OpenXR", "devices": "Quest, Vive, etc"},
            {"id": "meta_rayban", "name": "Meta Ray-Ban", "devices": "Ray-Ban Meta"},
            {"id": "xg_glass", "name": "XG Glass SDK", "devices": "Rokid, RayNeo"},
            {"id": "viture", "name": "Viture", "devices": "Viture XR"},
            {"id": "apple_vision", "name": "Apple Vision", "devices": "Vision Pro"},
            {"id": "steamvr", "name": "SteamVR", "devices": "PCVR headsets"}
        ],
        "note": "Hardwareless AI - True hardwareless XR integration"
    }


@router.post("/connect")
async def connect_platform(request: ConnectPlatformRequest):
    """Connect to an XR platform."""
    from core_engine.xr import VRPlatform, get_xr
    
    try:
        platform = VRPlatform(request.platform)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid platform")
    
    xr = get_xr()
    success = await xr.connect_platform(platform, request.config or {})
    
    return {
        "status": "connected" if success else "failed",
        "platform": request.platform
    }


@router.get("/devices")
async def list_devices():
    """List all connected XR devices."""
    from core_engine.xr import get_xr
    
    xr = get_xr()
    return {"devices": xr.get_connected_devices()}


@router.post("/display")
async def send_to_display(request: SendDisplayRequest):
    """Send content to XR device display."""
    from core_engine.xr import get_xr
    
    xr = get_xr()
    success = await xr.send_display(request.device_id, request.content)
    
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {"status": "sent", "device": request.device_id}


@router.post("/voice")
async def process_voice(audio_data: bytes):
    """Process voice input from XR device."""
    from core_engine.xr import get_xr
    
    xr = get_xr()
    result = await xr.process_voice(audio_data)
    
    return result


@router.post("/frame")
async def process_frame(frame_data: bytes):
    """Process camera frame from XR device."""
    from core_engine.xr import get_xr
    
    xr = get_xr()
    result = await xr.process_frame(frame_data)
    
    return result


@router.get("/capabilities/{capability}")
async def get_capability_platforms(capability: str):
    """Find platforms supporting a specific capability."""
    from core_engine.xr import get_xr
    
    xr = get_xr()
    platforms = xr.get_platforms_supporting(capability)
    
    return {
        "capability": capability,
        "platforms": [p.value for p in platforms]
    }
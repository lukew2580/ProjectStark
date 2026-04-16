"""
Hardwareless AI — Intel Network API Routes
Internal communication for threat intelligence sharing
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/intel", tags=["intel"])


class BroadcastAlertRequest(BaseModel):
    intel_type: str  # virus_alert, scam_alert, vulnerability, patch_ready
    priority: str    # routine, urgent, critical, action
    title: str
    content: str


class SendToTeamRequest(BaseModel):
    team: str        # virus_team, scam_team, security_team, research_team
    intel_type: str
    title: str
    content: str


class RegisterMemberRequest(BaseModel):
    member_id: str
    name: str
    role: str
    channel: str


class AcknowledgeRequest(BaseModel):
    message_id: str
    member_id: str


@router.get("/status")
async def get_intel_status():
    """Get Intel Network status."""
    from core_engine.intel_network import get_intel_network
    
    intel = get_intel_network()
    return intel.get_team_status()


@router.get("/teams")
async def get_teams():
    """Get available teams and their members."""
    from core_engine.intel_network import get_intel_network, Channel
    
    intel = get_intel_network()
    
    teams = {}
    for channel in Channel:
        members = intel.router.get_channel_members(channel)
        teams[channel.value] = {"member_count": len(members), "members": members}
    
    return {"teams": teams}


@router.post("/broadcast")
async def broadcast_alert(request: BroadcastAlertRequest):
    """Broadcast alert to all relevant teams."""
    from core_engine.intel_network import get_intel_network, IntelType, IntelPriority
    
    try:
        intel_type = IntelType(request.intel_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid intel_type")
    
    try:
        priority = IntelPriority(request.priority)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid priority")
    
    intel = get_intel_network()
    message = await intel.broadcast_alert(
        intel_type=intel_type,
        priority=priority,
        title=request.title,
        content=request.content
    )
    
    return {
        "message_id": message.message_id,
        "recipients": message.recipients,
        "delivered": len(message.recipients) > 0
    }


@router.post("/send/team")
async def send_to_team(request: SendToTeamRequest):
    """Send intel to specific team."""
    from core_engine.intel_network import get_intel_network, IntelType, Channel
    
    try:
        channel = Channel(request.team)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team")
    
    try:
        intel_type = IntelType(request.intel_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid intel_type")
    
    intel = get_intel_network()
    message = await intel.send_to_team(
        channel=channel,
        intel_type=intel_type,
        title=request.title,
        content=request.content
    )
    
    return {
        "message_id": message.message_id,
        "team": request.team,
        "delivered": True
    }


@router.post("/critical")
async def send_critical_alert(intel_type: str, title: str, content: str):
    """Send critical alert to all teams immediately."""
    from core_engine.intel_network import get_intel_network, IntelType
    
    try:
        itype = IntelType(intel_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid intel_type")
    
    intel = get_intel_network()
    message = await intel.send_critical_alert(
        intel_type=itype,
        title=title,
        content=content
    )
    
    return {
        "message_id": message.message_id,
        "broadcast_to": "all_teams",
        "priority": "critical"
    }


@router.post("/member/register")
async def register_member(request: RegisterMemberRequest):
    """Register a new team member."""
    from core_engine.intel_network import get_intel_network, Channel
    
    try:
        channel = Channel(request.channel)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel")
    
    intel = get_intel_network()
    intel.register_member(request.member_id, request.name, request.role, channel)
    
    return {
        "status": "registered",
        "member_id": request.member_id,
        "channel": request.channel
    }


@router.get("/messages/{member_id}")
async def get_member_messages(member_id: str):
    """Get messages for a specific member."""
    from core_engine.intel_network import get_intel_network
    
    intel = get_intel_network()
    messages = intel.get_member_messages(member_id)
    
    return {"messages": messages, "count": len(messages)}


@router.post("/acknowledge")
async def acknowledge_message(request: AcknowledgeRequest):
    """Acknowledge receipt of a message."""
    from core_engine.intel_network import get_intel_network
    
    intel = get_intel_network()
    intel.router.acknowledge_message(request.message_id, request.member_id)
    
    return {"status": "acknowledged", "message_id": request.message_id}


@router.post("/clear")
async def clear_acknowledged():
    """Clear acknowledged messages."""
    from core_engine.intel_network import get_intel_network
    
    intel = get_intel_network()
    intel.router.clear_acknowledged()
    
    return {"status": "cleared"}


@router.get("/bridge/platforms")
async def get_connected_platforms():
    """Get cross-platform bridge status."""
    from core_engine.intel_network import get_intel_bridge
    
    bridge = get_intel_bridge()
    return {
        "connected_platforms": bridge.get_connected_platforms(),
        "platforms_available": ["android", "ios", "web", "desktop"]
    }
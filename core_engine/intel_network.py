"""
Hardwareless AI — INTEL Network
Internal communication system for threat intelligence sharing
"""
import asyncio
import hashlib
import json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np

from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import similarity
from config.settings import DIMENSIONS


class IntelPriority(Enum):
    ROUTINE = "routine"       # Normal info
    URGENT = "urgent"         # Needs attention
    CRITICAL = "critical"     # Immediate action
    ACTION_REQUIRED = "action"  # Requires specific response


class IntelType(Enum):
    VIRUS_ALERT = "virus_alert"
    SCAM_ALERT = "scam_alert"
    VULNERABILITY = "vulnerability"
    THREAT_PATTERN = "threat_pattern"
    PATCH_READY = "patch_ready"
    SITUATION_REPORT = "situation_report"


class Channel(Enum):
    ALL = "all"
    VIRUS_TEAM = "virus_team"
    SCAM_TEAM = "scam_team"
    SECURITY_TEAM = "security_team"
    RESEARCH_TEAM = "research_team"
    BRIDGE_NET = "bridge_net"  # Cross-platform comms


@dataclass
class IntelMessage:
    """Intelligence message for internal communication."""
    message_id: str
    channel: Channel
    intel_type: IntelType
    priority: IntelPriority
    title: str
    content: str
    source_node: str
    timestamp: str
    recipients: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class TeamMember:
    """A member of the internal team."""
    member_id: str
    name: str
    role: str
    channel: Channel
    online: bool = True
    last_seen: str = ""


class IntelRouter:
    """
    Routes intelligence to the right people/teams.
    
    Think of it as a secure internal news desk:
    - Virus alerts → virus team
    - Scam patterns → scam team  
    - Critical threats → all teams
    """
    
    def __init__(self):
        self._channels: Dict[Channel, List[str]] = {
            Channel.ALL: [],
            Channel.VIRUS_TEAM: [],
            Channel.SCAM_TEAM: [],
            Channel.SECURITY_TEAM: [],
            Channel.RESEARCH_TEAM: [],
            Channel.BRIDGE_NET: []
        }
        
        self._message_queue: List[IntelMessage] = []
        self._subscribers: Dict[str, List[str]] = {}
        self._route_rules: Dict[IntelType, List[Channel]] = self._setup_routing()
    
    def _setup_routing(self) -> Dict[IntelType, List[Channel]]:
        """Set up routing rules for different intel types."""
        return {
            IntelType.VIRUS_ALERT: [Channel.VIRUS_TEAM, Channel.ALL],
            IntelType.SCAM_ALERT: [Channel.SCAM_TEAM, Channel.ALL],
            IntelType.VULNERABILITY: [Channel.SECURITY_TEAM, Channel.RESEARCH_TEAM],
            IntelType.THREAT_PATTERN: [Channel.RESEARCH_TEAM, Channel.VIRUS_TEAM, Channel.SCAM_TEAM],
            IntelType.PATCH_READY: [Channel.ALL],
            IntelType.SITUATION_REPORT: [Channel.ALL],
        }
    
    def route_intel(self, message: IntelMessage) -> List[str]:
        """Route intel to appropriate channels."""
        target_channels = self._route_rules.get(message.intel_type, [Channel.ALL])
        
        recipients = []
        for channel in target_channels:
            recipients.extend(self._channels.get(channel, []))
        
        recipients = list(set(recipients))  # Deduplicate
        message.recipients = recipients
        self._message_queue.append(message)
        
        return recipients
    
    def subscribe(self, member_id: str, channel: Channel):
        """Subscribe a member to a channel."""
        if channel not in self._channels:
            self._channels[channel] = []
        if member_id not in self._channels[channel]:
            self._channels[channel].append(member_id)
    
    def unsubscribe(self, member_id: str, channel: Channel):
        """Unsubscribe from channel."""
        if channel in self._channels and member_id in self._channels[channel]:
            self._channels[channel].remove(member_id)
    
    def get_channel_members(self, channel: Channel) -> List[str]:
        """Get all members in a channel."""
        return self._channels.get(channel, [])
    
    def get_pending_messages(self, member_id: str) -> List[IntelMessage]:
        """Get messages for a specific member."""
        messages = []
        for msg in self._message_queue:
            if member_id in msg.recipients:
                messages.append(msg)
        return messages
    
    def acknowledge_message(self, message_id: str, member_id: str):
        """Mark message as acknowledged."""
        for msg in self._message_queue:
            if msg.message_id == message_id:
                if "acknowledged_by" not in msg.metadata:
                    msg.metadata["acknowledged_by"] = []
                msg.metadata["acknowledged_by"].append(member_id)
    
    def clear_acknowledged(self):
        """Clear old acknowledged messages."""
        self._message_queue = [
            msg for msg in self._message_queue 
            if len(msg.metadata.get("acknowledged_by", [])) < len(msg.recipients)
        ]


class IntelNetwork:
    """
    Main Intel Network - coordinates all internal communications.
    
    Functions:
    - Broadcast alerts to teams
    - Route specific intel to specialists
    - Track message delivery/acknowledgment
    - Maintain team roster
    """
    
    def __init__(self):
        self.router = IntelRouter()
        self._members: Dict[str, TeamMember] = {}
        self._node_id = hashlib.md5(b"intel_node").hexdigest()[:8]
    
    def register_member(self, member_id: str, name: str, role: str, channel: Channel):
        """Register a new team member."""
        member = TeamMember(
            member_id=member_id,
            name=name,
            role=role,
            channel=channel,
            online=True,
            last_seen=datetime.now().isoformat()
        )
        self._members[member_id] = member
        self.router.subscribe(member_id, channel)
    
    async def broadcast_alert(
        self,
        intel_type: IntelType,
        priority: IntelPriority,
        title: str,
        content: str,
        source: str = "system"
    ) -> IntelMessage:
        """Broadcast an alert to relevant teams."""
        message = IntelMessage(
            message_id=hashlib.sha256(f"{datetime.now()}".encode()).hexdigest()[:12],
            channel=Channel.ALL,
            intel_type=intel_type,
            priority=priority,
            title=title,
            content=content,
            source_node=source,
            timestamp=datetime.now().isoformat()
        )
        
        recipients = self.router.route_intel(message)
        return message
    
    async def send_to_team(
        self,
        channel: Channel,
        intel_type: IntelType,
        title: str,
        content: str,
        source: str = "system"
    ) -> IntelMessage:
        """Send intel to specific team."""
        message = IntelMessage(
            message_id=hashlib.sha256(f"{datetime.now()}".encode()).hexdigest()[:12],
            channel=channel,
            intel_type=intel_type,
            priority=IntelPriority.ROUTINE,
            title=title,
            content=content,
            source_node=source,
            timestamp=datetime.now().isoformat()
        )
        
        recipients = self.router.route_intel(message)
        return message
    
    async def send_critical_alert(
        self,
        intel_type: IntelType,
        title: str,
        content: str,
        source: str = "system"
    ) -> IntelMessage:
        """Send critical alert to all teams immediately."""
        message = IntelMessage(
            message_id=hashlib.sha256(f"critical_{datetime.now()}".encode()).hexdigest()[:12],
            channel=Channel.ALL,
            intel_type=intel_type,
            priority=IntelPriority.CRITICAL,
            title=f"🚨 CRITICAL: {title}",
            content=content,
            source_node=source,
            timestamp=datetime.now().isoformat()
        )
        
        recipients = self.router.route_intel(message)
        return message
    
    def get_team_status(self) -> Dict:
        """Get status of all teams."""
        return {
            "teams": {
                "virus_team": len(self.router.get_channel_members(Channel.VIRUS_TEAM)),
                "scam_team": len(self.router.get_channel_members(Channel.SCAM_TEAM)),
                "security_team": len(self.router.get_channel_members(Channel.SECURITY_TEAM)),
                "research_team": len(self.router.get_channel_members(Channel.RESEARCH_TEAM)),
            },
            "pending_messages": len(self.router._message_queue),
            "total_members": len(self._members),
            "node_id": self._node_id
        }
    
    def get_member_messages(self, member_id: str) -> List[Dict]:
        """Get messages for a member."""
        messages = self.router.get_pending_messages(member_id)
        return [
            {
                "id": m.message_id,
                "type": m.intel_type.value,
                "priority": m.priority.value,
                "title": m.title,
                "content": m.content[:100] + "..." if len(m.content) > 100 else m.content,
                "timestamp": m.timestamp,
                "acknowledged": member_id in m.metadata.get("acknowledged_by", [])
            }
            for m in messages
        ]


class CrossPlatformBridge:
    """
    Bridges intel across different platform nodes.
    Android ↔ iOS ↔ Web ↔ Desktop
    """
    
    def __init__(self, intel_network: IntelNetwork):
        self.intel = intel_network
        self._connected_nodes: Dict[str, str] = {}
    
    def register_node(self, node_id: str, platform: str):
        """Register a platform node."""
        self._connected_nodes[node_id] = platform
    
    async def broadcast_cross_platform(
        self,
        intel_type: IntelType,
        title: str,
        content: str
    ):
        """Broadcast intel across all connected platforms."""
        message = IntelMessage(
            message_id=hashlib.sha256(f"cross_{datetime.now()}".encode()).hexdigest()[:12],
            channel=Channel.BRIDGE_NET,
            intel_type=intel_type,
            priority=IntelPriority.URGENT,
            title=title,
            content=content,
            source_node=f"bridge_{len(self._connected_nodes)}",
            timestamp=datetime.now().isoformat(),
            metadata={"platforms": list(self._connected_nodes.values())}
        )
        
        self.intel.router.route_intel(message)
        return message
    
    def get_connected_platforms(self) -> List[str]:
        """Get list of connected platforms."""
        return list(set(self._connected_nodes.values()))


_global_intel_network: Optional[IntelNetwork] = None
_global_bridge: Optional[CrossPlatformBridge] = None


def get_intel_network() -> IntelNetwork:
    global _global_intel_network
    if _global_intel_network is None:
        _global_intel_network = IntelNetwork()
        _setup_default_members(_global_intel_network)
    return _global_intel_network


def get_intel_bridge() -> CrossPlatformBridge:
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = CrossPlatformBridge(get_intel_network())
    return _global_bridge


def _setup_default_members(network: IntelNetwork):
    """Setup default team members."""
    network.register_member("virus_ops_1", "Virus Operations 1", "Analyst", Channel.VIRUS_TEAM)
    network.register_member("virus_ops_2", "Virus Operations 2", "Analyst", Channel.VIRUS_TEAM)
    network.register_member("scam_ops_1", "Scam Operations 1", "Analyst", Channel.SCAM_TEAM)
    network.register_member("scam_ops_2", "Scam Operations 2", "Analyst", Channel.SCAM_TEAM)
    network.register_member("security_lead", "Security Lead", "Manager", Channel.SECURITY_TEAM)
    network.register_member("research_lead", "Research Lead", "Manager", Channel.RESEARCH_TEAM)
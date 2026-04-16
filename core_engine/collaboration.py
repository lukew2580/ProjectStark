"""
Agent Collaboration Protocols
Defines how agents work together
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ProtocolType(Enum):
    REQUEST_RESPONSE = "request_response"
    BROADCAST = "broadcast"
    CHAIN = "chain"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"


@dataclass
class CollaborationMessage:
    sender: str
    recipient: str
    message_type: ProtocolType
    content: Dict
    timestamp: str


class AgentCollaboration:
    """
    Defines collaboration protocols between agents.
    
    Protocols:
    - Request-Response: One agent requests, other responds
    - Broadcast: One agent broadcasts to all
    - Chain: Sequential processing
    - Parallel: Simultaneous processing
    - Hierarchical: Supervisor-worker
    """
    
    def __init__(self):
        self.message_queue: List[CollaborationMessage] = []
        self.active_sessions: Dict[str, Dict] = {}
    
    async def request_response(
        self,
        sender: str,
        recipient: str,
        request: Dict
    ) -> Dict:
        """Request-response protocol."""
        message = CollaborationMessage(
            sender=sender,
            recipient=recipient,
            message_type=ProtocolType.REQUEST_RESPONSE,
            content=request,
            timestamp=datetime.now().isoformat()
        )
        self.message_queue.append(message)
        
        return {
            "status": "sent",
            "sender": sender,
            "recipient": recipient,
            "message_id": len(self.message_queue) - 1
        }
    
    async def broadcast(
        self,
        sender: str,
        recipients: List[str],
        message: Dict
    ) -> Dict:
        """Broadcast to multiple agents."""
        messages = []
        
        for recipient in recipients:
            msg = CollaborationMessage(
                sender=sender,
                recipient=recipient,
                message_type=ProtocolType.BROADCAST,
                content=message,
                timestamp=datetime.now().isoformat()
            )
            self.message_queue.append(msg)
            messages.append(msg)
        
        return {
            "status": "broadcast",
            "recipients": recipients,
            "count": len(recipients)
        }
    
    async def chain_execute(
        self,
        agents: List[str],
        initial_data: Dict
    ) -> List[Dict]:
        """Chain execution: sequential processing."""
        results = []
        current_data = initial_data
        
        for agent in agents:
            result = {
                "agent": agent,
                "input": current_data,
                "output": f"Processed by {agent}",
                "timestamp": datetime.now().isoformat()
            }
            results.append(result)
            current_data = result
        
        return results
    
    async def parallel_execute(
        self,
        agents: List[str],
        data: Dict
    ) -> List[Dict]:
        """Parallel execution: simultaneous processing."""
        results = []
        
        for agent in agents:
            result = {
                "agent": agent,
                "input": data,
                "output": f"Processed by {agent}",
                "timestamp": datetime.now().isoformat()
            }
            results.append(result)
        
        return results
    
    async def hierarchical_execute(
        self,
        supervisor: str,
        workers: List[str],
        task: Dict
    ) -> Dict:
        """Hierarchical: supervisor assigns to workers."""
        # Supervisor analyzes task
        assigned_workers = workers[:len(workers)//2] if len(workers) > 1 else workers
        
        results = []
        for worker in assigned_workers:
            results.append({
                "worker": worker,
                "task": task,
                "status": "assigned",
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "supervisor": supervisor,
            "workers_assigned": assigned_workers,
            "results": results
        }
    
    def get_messages(self, limit: int = 100) -> List[Dict]:
        """Get message history."""
        return [
            {
                "sender": m.sender,
                "recipient": m.recipient,
                "type": m.message_type.value,
                "timestamp": m.timestamp
            }
            for m in self.message_queue[-limit:]
        ]


_global_collaboration: Optional[AgentCollaboration] = None


def get_agent_collaboration() -> AgentCollaboration:
    global _global_collaboration
    if _global_collaboration is None:
        _global_collaboration = AgentCollaboration()
    return _global_collaboration
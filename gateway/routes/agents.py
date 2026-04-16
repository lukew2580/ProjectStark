"""
Hardwareless AI — Agent Router API Routes
HDC-based agent routing endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/agents", tags=["agents"])


class RouteRequest(BaseModel):
    input_text: str
    language: str = "en"


class HandleRequest(BaseModel):
    input_text: str
    language: str = "en"
    context: Optional[Dict[str, Any]] = None


class RegisterAgentRequest(BaseModel):
    name: str
    description: str
    instructions: str
    domains: List[str]
    is_default: bool = False


class EscalateRequest(BaseModel):
    from_agent: str
    to_agent: str
    context: Dict[str, Any]


@router.get("/list")
async def list_agents():
    """List all registered agents."""
    from core_engine.agent_router import get_router
    
    router = get_router()
    return {"agents": router.get_available_agents()}


@router.post("/route")
async def route_to_agent(request: RouteRequest):
    """Route input to the best matching agent (returns agent name only)."""
    from core_engine.agent_router import get_router
    
    router = get_router()
    agent_name = router.route(request.input_text, request.language)
    
    return {
        "input": request.input_text,
        "routed_to": agent_name,
        "language": request.language
    }


@router.post("/handle")
async def handle_with_agent(request: HandleRequest):
    """Route and handle input through the agent system."""
    from core_engine.agent_router import get_router
    
    router = get_router()
    result = await router.handle(
        request.input_text,
        request.language,
        request.context
    )
    
    return result


@router.post("/register")
async def register_agent(request: RegisterAgentRequest):
    """Register a new specialist agent."""
    from core_engine.agent_router import get_router
    
    router = get_router()
    router.register_agent(
        name=request.name,
        description=request.description,
        instructions=request.instructions,
        domains=request.domains,
        is_default=request.is_default
    )
    
    return {
        "status": "registered",
        "agent": request.name,
        "domains": request.domains
    }


@router.post("/escalate")
async def escalate_to_agent(request: EscalateRequest):
    """Escalate a conversation from one agent to another."""
    from core_engine.agent_router import get_swarm
    
    swarm = get_swarm()
    result = await swarm.escalate(
        request.from_agent,
        request.to_agent,
        request.context
    )
    
    return result


@router.get("/stats")
async def get_agent_stats():
    """Get agent routing statistics."""
    from core_engine.agent_router import get_swarm
    
    swarm = get_swarm()
    return swarm.get_routing_stats()


@router.post("/broadcast")
async def broadcast_message(from_agent: str, message: str):
    """Broadcast message to all agents."""
    from core_engine.agent_router import get_swarm
    
    swarm = get_swarm()
    await swarm.broadcast(message, from_agent)
    
    return {"status": "broadcasted", "from": from_agent, "message": message}
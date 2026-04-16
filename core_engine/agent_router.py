"""
Hardwareless AI — HDC Agent Router
Routes inputs to specialist agents via hypervector similarity
"""
import asyncio
import hashlib
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import bind, bundle, similarity
from core_engine.translation import get_language_matrix
from config.settings import DIMENSIONS


@dataclass
class SpecialistAgent:
    """
    A specialist agent that handles specific tasks.
    Routed to via HDC hypervector similarity.
    """
    name: str
    description: str
    instructions: str
    domains: List[str]  # Keywords this agent handles
    domain_vector: np.ndarray = field(init=False)
    tools: List[Callable] = field(default_factory=list)
    
    def __post_init__(self):
        self.domain_vector = self._create_domain_vector()
    
    def _create_domain_vector(self) -> np.ndarray:
        """Create hypervector from domain keywords."""
        domain_str = " ".join(self.domains)
        seed = hash(domain_str) % (2**31)
        return generate_random_vector(DIMENSIONS, seed=seed)


class HDCAgentRouter:
    """
    HDC-based agent router.
    
    Instead of LLM-based routing, uses hypervector similarity
    to determine which specialist should handle a request.
    
    Architecture:
    - Each specialist has a domain hypervector
    - Input is encoded as hypervector
    - Route to highest-similarity specialist
    - Fall back to general agent if no match
    """
    
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self.agents: Dict[str, SpecialistAgent] = {}
        self.default_agent: Optional[str] = None
        self._language_matrix = get_language_matrix()
        
    def register_agent(
        self,
        name: str,
        description: str,
        instructions: str,
        domains: List[str],
        is_default: bool = False
    ):
        """Register a specialist agent."""
        agent = SpecialistAgent(
            name=name,
            description=description,
            instructions=instructions,
            domains=domains
        )
        self.agents[name] = agent
        
        if is_default or not self.default_agent:
            self.default_agent = name
    
    def register_tool(self, agent_name: str, tool: Callable):
        """Register a tool for an agent."""
        if agent_name in self.agents:
            self.agents[agent_name].tools.append(tool)
    
    def route(self, input_text: str, language: str = "en") -> str:
        """
        Route input to the best matching specialist agent.
        Returns agent name.
        """
        if not self.agents:
            return self.default_agent or "general"
        
        input_vector = self._encode_input(input_text, language)
        
        best_agent = self.default_agent
        best_score = -1.0
        
        for name, agent in self.agents.items():
            score = similarity(input_vector, agent.domain_vector, self.dimensions)
            if score > best_score:
                best_score = score
                best_agent = name
        
        return best_agent
    
    def _encode_input(self, text: str, language: str) -> np.ndarray:
        """Encode input text as hypervector."""
        return self._language_matrix.encode_text(text.lower(), language)
    
    async def handle(
        self,
        input_text: str,
        language: str = "en",
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Route and handle input through the agent system.
        """
        agent_name = self.route(input_text, language)
        agent = self.agents.get(agent_name)
        
        if not agent:
            return {"error": "No agent found", "agent": agent_name}
        
        result = {
            "routed_to": agent_name,
            "description": agent.description,
            "instructions": agent.instructions,
            "input": input_text,
            "language": language
        }
        
        if agent.tools:
            tool_results = []
            for tool in agent.tools:
                if asyncio.iscoroutinefunction(tool):
                    tool_result = await tool(input_text, context or {})
                else:
                    tool_result = tool(input_text, context or {})
                tool_results.append(tool_result)
            result["tool_results"] = tool_results
        
        return result
    
    def get_available_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        return [
            {
                "name": name,
                "description": agent.description,
                "domains": agent.domains,
                "is_default": name == self.default_agent,
                "tool_count": len(agent.tools)
            }
            for name, agent in self.agents.items()
        ]
    
    def add_domain_keyword(self, agent_name: str, keyword: str):
        """Add a keyword to an agent's domain for better routing."""
        if agent_name in self.agents:
            agent = self.agents[agent_name]
            agent.domains.append(keyword)
            agent.domain_vector = agent._create_domain_vector()


class AgentSwarm:
    """
    Swarm of agents that can collaborate.
    Uses HDC for implicit communication.
    """
    
    def __init__(self, router: HDCAgentRouter):
        self.router = router
        self._message_log: List[Dict] = []
    
    async def broadcast(
        self,
        message: str,
        sender: str,
        exclude: List[str] = None
    ):
        """Broadcast message to all agents."""
        exclude = exclude or []
        
        for name, agent in self.router.agents.items():
            if name != sender and name not in exclude:
                self._message_log.append({
                    "from": sender,
                    "to": name,
                    "message": message
                })
    
    async def escalate(
        self,
        from_agent: str,
        to_agent: str,
        context: Dict
    ) -> Dict:
        """Escalate to another agent with context."""
        to = self.router.agents.get(to_agent)
        if not to:
            return {"error": f"Agent {to_agent} not found"}
        
        return await self.router.handle(
            input_text=context.get("summary", ""),
            language=context.get("language", "en"),
            context={"escalated_from": from_agent, **context}
        )
    
    def get_routing_stats(self) -> Dict:
        """Get routing statistics."""
        if not self._message_log:
            return {"total_messages": 0, "agents": {}}
        
        agent_counts = {}
        for msg in self._message_log:
            to = msg["to"]
            agent_counts[to] = agent_counts.get(to, 0) + 1
        
        return {
            "total_messages": len(self._message_log),
            "agents": agent_counts
        }


_global_router: Optional[HDCAgentRouter] = None
_global_swarm: Optional[AgentSwarm] = None


def get_router() -> HDCAgentRouter:
    global _global_router
    if _global_router is None:
        _global_router = HDCAgentRouter()
        _setup_default_agents(_global_router)
    return _global_router


def get_swarm() -> AgentSwarm:
    global _global_swarm
    if _global_swarm is None:
        _global_swarm = AgentSwarm(get_router())
    return _global_swarm


def _setup_default_agents(router: HDCAgentRouter):
    """Set up default specialist agents."""
    router.register_agent(
        name="general",
        description="General purpose assistant",
        instructions="Help with any question. Use other specialists when needed.",
        domains=["help", "question", "general", "anything"],
        is_default=True
    )
    
    router.register_agent(
        name="billing",
        description="Handles invoices, payments, subscriptions",
        instructions="Handle billing inquiries. Process refunds when valid.",
        domains=["invoice", "payment", "bill", "refund", "charge", "subscription", "price", "cost"]
    )
    
    router.register_agent(
        name="technical",
        description="Handles technical issues and bugs",
        instructions="Diagnose and resolve technical problems.",
        domains=["bug", "error", "crash", "not working", "broken", "fix", "issue", "problem"]
    )
    
    router.register_agent(
        name="translator",
        description="Handles translation requests",
        instructions="Translate text between languages accurately.",
        domains=["translate", "translation", "language", "convert", "spanish", "french", "chinese"]
    )
    
    router.register_agent(
        name="research",
        description="Handles research and information lookup",
        instructions="Find and summarize information accurately.",
        domains=["search", "find", "research", "information", "lookup", "what is", "how does"]
    )
    
    router.register_agent(
        name="coder",
        description="Handles code-related requests",
        instructions="Write, debug, and explain code.",
        domains=["code", "programming", "script", "function", "class", "debug", "syntax"]
    )
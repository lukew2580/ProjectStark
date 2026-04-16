"""
Multi-Agent Orchestration System
Coordinates multiple agents for complex tasks
"""
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class AgentRole(Enum):
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    EXECUTOR = "executor"
    VERIFIER = "verifier"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class AgentTask:
    task_id: str
    agent_name: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    input_data: Dict = field(default_factory=dict)
    output_data: Optional[Dict] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Agent:
    name: str
    role: AgentRole
    description: str
    capabilities: List[str]
    system_prompt: str = ""
    tools: List[Callable] = field(default_factory=list)


class MultiAgentOrchestrator:
    """
    Coordinates multiple agents for complex tasks.
    
    Architecture:
    - Coordinator: Breaks down tasks
    - Specialists: Execute specific domains
    - Executors: Run tools/actions
    - Verifiers: Validate results
    """
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, AgentTask] = {}
        self.task_history: List[AgentTask] = []
        self._register_default_agents()
    
    def _register_default_agents(self):
        """Register default agents."""
        default_agents = [
            Agent(
                name="coordinator",
                role=AgentRole.COORDINATOR,
                description="Breaks down complex tasks into subtasks",
                capabilities=["task decomposition", "routing", "planning"],
                system_prompt="You are a task coordinator. Break down user requests into subtasks and assign to appropriate specialists."
            ),
            Agent(
                name="virus_specialist",
                role=AgentRole.SPECIALIST,
                description="Handles virus/malware analysis",
                capabilities=["virus detection", "malware analysis", "quarantine"],
                system_prompt="You specialize in virus and malware detection using HDC hypervector similarity."
            ),
            Agent(
                name="scam_specialist", 
                role=AgentRole.SPECIALIST,
                description="Handles scam detection",
                capabilities=["phone analysis", "email analysis", "website analysis"],
                system_prompt="You specialize in detecting phone, email, and website scams."
            ),
            Agent(
                name="translator_specialist",
                role=AgentRole.SPECIALIST,
                description="Handles translation tasks",
                capabilities=["translate", "language detection"],
                system_prompt="You specialize in multilingual translation."
            ),
            Agent(
                name="executor",
                role=AgentRole.EXECUTOR,
                description="Executes approved actions",
                capabilities=["run tools", "execute code"],
                system_prompt="You execute approved actions and tools."
            ),
            Agent(
                name="verifier",
                role=AgentRole.VERIFIER,
                description="Verifies results",
                capabilities=["validate", "check", "verify"],
                system_prompt="You verify results are correct and complete."
            )
        ]
        
        for agent in default_agents:
            self.agents[agent.name] = agent
    
    def register_agent(self, agent: Agent):
        """Register a new agent."""
        self.agents[agent.name] = agent
    
    async def execute_task(
        self,
        task: str,
        context: Dict = None
    ) -> Dict:
        """Execute a task using multiple agents."""
        task_id = f"task_{datetime.now().timestamp()}"
        
        # Decompose task using coordinator
        subtasks = await self._decompose_task(task)
        
        results = []
        
        for subtask in subtasks:
            # Route to appropriate specialist
            agent_name = self._route_to_agent(subtask)
            agent = self.agents.get(agent_name)
            
            if not agent:
                continue
            
            # Execute subtask
            agent_task = AgentTask(
                task_id=f"{task_id}_{agent_name}",
                agent_name=agent_name,
                description=subtask,
                status=TaskStatus.RUNNING,
                started_at=datetime.now().isoformat()
            )
            
            self.tasks[agent_task.task_id] = agent_task
            
            # Simulate execution (in real impl, would call agent)
            agent_task.output_data = {"result": f"Processed: {subtask}"}
            agent_task.status = TaskStatus.COMPLETED
            agent_task.completed_at = datetime.now().isoformat()
            
            results.append(agent_task.output_data)
            self.task_history.append(agent_task)
        
        return {
            "task": task,
            "subtasks": len(subtasks),
            "results": results,
            "status": "completed"
        }
    
    async def _decompose_task(self, task: str) -> List[str]:
        """Decompose task into subtasks."""
        # Simple keyword-based decomposition
        subtasks = []
        
        if any(w in task.lower() for w in ["virus", "malware", "scan", "infected"]):
            subtasks.append("virus_analysis")
        
        if any(w in task.lower() for w in ["scam", "phishing", "fake", "phone"]):
            subtasks.append("scam_analysis")
        
        if any(w in task.lower() for w in ["translate", "spanish", "french", "chinese"]):
            subtasks.append("translation")
        
        if not subtasks:
            subtasks = [task]
        
        return subtasks
    
    def _route_to_agent(self, subtask: str) -> str:
        """Route subtask to appropriate agent."""
        routing = {
            "virus_analysis": "virus_specialist",
            "scam_analysis": "scam_specialist",
            "translation": "translator_specialist"
        }
        return routing.get(subtask, "executor")
    
    def get_agents(self) -> List[Dict]:
        """Get all registered agents."""
        return [
            {
                "name": a.name,
                "role": a.role.value,
                "description": a.description,
                "capabilities": a.capabilities
            }
            for a in self.agents.values()
        ]
    
    def get_task_history(self, limit: int = 100) -> List[Dict]:
        """Get task execution history."""
        return [
            {
                "task_id": t.task_id,
                "agent": t.agent_name,
                "description": t.description,
                "status": t.status.value,
                "started": t.started_at,
                "completed": t.completed_at
            }
            for t in self.task_history[-limit:]
        ]


_global_orchestrator: Optional[MultiAgentOrchestrator] = None


def get_multi_agent_orchestrator() -> MultiAgentOrchestrator:
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = MultiAgentOrchestrator()
    return _global_orchestrator
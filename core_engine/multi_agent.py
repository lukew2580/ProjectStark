"""
Hardwareless AI — Multi-Agent Orchestration System
Advanced AI coordination, collaboration, and swarm intelligence.
"""
import asyncio
import hashlib
import secrets
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone

from config.settings import DIMENSIONS
from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import bind, bundle, similarity


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"


class AgentRole(Enum):
    COORDINATOR = "coordinator"
    WORKER = "worker"
    MONITOR = "monitor"
    ROUTER = "router"
    SECURITY = "security"
    ANALYZER = "analyzer"


@dataclass
class AgentConfig:
    role: AgentRole
    name: str
    capabilities: List[str]
    max_concurrent_tasks: int = 3
    priority: int = 5


@dataclass
class Task:
    task_id: str
    name: str
    description: str
    input_data: Any
    assigned_to: Optional[int] = None
    status: str = "pending"
    result: Any = None
    created_at: str = ""
    completed_at: Optional[str] = None


@dataclass
class AgentMessage:
    message_id: str
    from_agent: int
    to_agent: int
    message_type: str
    content: Any
    timestamp: str
    requires_ack: bool = False


class Agent:
    def __init__(self, agent_id: int, config: AgentConfig):
        self.agent_id = agent_id
        self.config = config
        self.state = AgentState.IDLE
        self._vector = generate_random_vector(DIMENSIONS, seed=agent_id)
        self._tasks: List[Task] = []
        self._inbox: List[AgentMessage] = []
        self._memory: Dict[str, Any] = {}
        self._stats = {"tasks_completed": 0, "tasks_failed": 0, "messages_sent": 0, "messages_received": 0}
    
    async def think(self, input_data: Any) -> Any:
        self.state = AgentState.THINKING
        self.state = AgentState.IDLE
        return f"Processed by {self.config.name}"
    
    async def act(self, action: Callable, *args, **kwargs) -> Any:
        self.state = AgentState.ACTING
        try:
            result = await action(*args, **kwargs)
            self._stats["tasks_completed"] += 1
            return result
        except Exception:
            self._stats["tasks_failed"] += 1
            raise
        finally:
            self.state = AgentState.IDLE
    
    def receive_message(self, message: AgentMessage):
        self._inbox.append(message)
        self._stats["messages_received"] += 1
    
    def get_state(self) -> Dict:
        return {
            "id": self.agent_id,
            "name": self.config.name,
            "role": self.config.role.value,
            "state": self.state.value,
            "pending": len(self._tasks),
            "stats": self._stats
        }


class MultiAgentOrchestrator:
    def __init__(self):
        self._agents: Dict[int, Agent] = {}
        self._tasks: Dict[str, Task] = {}
        self._message_log: List[AgentMessage] = []
        self._coordinator_id: Optional[int] = None
        self._round_robin: int = 0
    
    def create_agent(self, config: AgentConfig) -> int:
        agent_id = len(self._agents) + 1
        self._agents[agent_id] = Agent(agent_id, config)
        if config.role == AgentRole.COORDINATOR and self._coordinator_id is None:
            self._coordinator_id = agent_id
        return agent_id
    
    def get_agent(self, agent_id: int) -> Optional[Agent]:
        return self._agents.get(agent_id)
    
    def find_by_role(self, role: AgentRole) -> List[Agent]:
        return [a for a in self._agents.values() if a.config.role == role]
    
    def assign_task(self, task: Task, agent_id: int = None) -> bool:
        if agent_id is None:
            agent_id = self._next_agent()
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        task.assigned_to = agent_id
        self._tasks[task.task_id] = task
        return True
    
    def _next_agent(self) -> int:
        active = [a for a in self._agents.values() if a.state == AgentState.IDLE]
        if not active:
            return self._coordinator_id or 1
        self._round_robin = (self._round_robin + 1) % len(active)
        return active[self._round_robin].agent_id
    
    async def execute_task(self, task_id: str) -> Any:
        task = self._tasks.get(task_id)
        agent = self._agents.get(task.assigned_to) if task else None
        if not task or not agent:
            raise ValueError("Task/agent not found")
        task.status = "running"
        task.result = await agent.think(task.input_data)
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc).isoformat()
        return task.result
    
    async def execute_parallel(self, names: List[str], data: Any) -> List[Any]:
        tasks = []
        for name in names:
            task = Task(secrets.token_hex(8), name, name, data)
            if self.assign_task(task):
                tasks.append(task)
        results = await asyncio.gather(*[self.execute_task(t.task_id) for t in tasks], return_exceptions=True)
        return results
    
    def send_message(self, fr: int, to: int, mtype: str, content: Any) -> bool:
        if fr not in self._agents or to not in self._agents:
            return False
        msg = AgentMessage(secrets.token_hex(8), fr, to, mtype, content, datetime.now(timezone.utc).isoformat())
        self._agents[to].receive_message(msg)
        self._message_log.append(msg)
        self._agents[fr]._stats["messages_sent"] += 1
        return True
    
    def get_state(self) -> Dict:
        return {
            "agents": len(self._agents),
            "tasks": len(self._tasks),
            "coordinator": self._coordinator_id,
            "states": [a.get_state() for a in self._agents.values()]
        }


class SwarmHealing:
    def __init__(self, orchestrator: MultiAgentOrchestrator):
        self.orchestrator = orchestrator
        self._checks: Dict[str, Callable] = {}
        self._actions: Dict[str, Callable] = {}
    
    def register_check(self, name: str, check: Callable):
        self._checks[name] = check
    
    def register_action(self, name: str, action: Callable):
        self._actions[name] = action
    
    async def run_checks(self) -> Dict:
        results = {}
        for name, check in self._checks.items():
            results[name] = await check() if asyncio.iscoroutinefunction(check) else check()
        return results
    
    async def heal(self) -> List[str]:
        results = await self.run_checks()
        actions = []
        for name, r in results.items():
            if r.get("status") == "unhealthy":
                action = self._actions.get(name)
                if action:
                    await action() if asyncio.iscoroutinefunction(action) else action()
                    actions.append(name)
        return actions
    
    def get_health(self) -> Dict:
        return {"checks": len(self._checks), "agents": len(self.orchestrator._agents)}


_orchestrator: Optional[MultiAgentOrchestrator] = None


def get_orchestrator() -> MultiAgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator


def create_default_swarm() -> MultiAgentOrchestrator:
    orch = MultiAgentOrchestrator()
    orch.create_agent(AgentConfig(AgentRole.COORDINATOR, "Coordinator", ["orchestrate"], priority=10))
    for i in range(3):
        orch.create_agent(AgentConfig(AgentRole.WORKER, f"Worker-{i+1}", ["process"]))
    orch.create_agent(AgentConfig(AgentRole.MONITOR, "Monitor", ["monitor"]))
    orch.create_agent(AgentConfig(AgentRole.SECURITY, "Security", ["protect"]))
    return orch
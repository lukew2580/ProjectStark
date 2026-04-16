"""
Hardwareless AI — Skills API Routes
Execute and manage skills via HTTP
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/skills", tags=["skills"])


class ExecuteSkillRequest(BaseModel):
    skill_name: str
    context: Optional[Dict[str, Any]] = {}
    args: Optional[Dict[str, Any]] = {}


class SetKeysRequest(BaseModel):
    user_id: str
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    google_key: Optional[str] = None
    deepseek_key: Optional[str] = None
    custom_keys: Optional[Dict[str, str]] = None


@router.get("/list")
async def list_skills():
    """List all available skills."""
    from core_engine.skills import get_skills
    
    registry = get_skills()
    return {"skills": registry.list_skills()}


@router.post("/execute")
async def execute_skill(request: ExecuteSkillRequest):
    """Execute a skill by name."""
    from core_engine.skills import get_skills
    import asyncio
    
    registry = get_skills()
    
    result = await registry.execute(
        request.skill_name,
        request.context or {},
        request.args or {}
    )
    
    return {"skill": request.skill_name, "result": result}


@router.post("/reload")
async def reload_skills():
    """Reload all skills from disk."""
    from core_engine.skills import get_skills
    
    registry = get_skills()
    registry.reload()
    
    return {"status": "reloaded", "skills_count": len(registry.list_skills())}


@router.get("/search")
async def search_skills(q: str):
    """Search skills by trigger or name."""
    from core_engine.skills import get_skills
    
    registry = get_skills()
    skills = registry.list_skills()
    
    q_lower = q.lower()
    matches = [
        s for s in skills 
        if q_lower in s["name"].lower() or any(q_lower in t.lower() for t in s.get("triggers", []))
    ]
    
    return {"query": q, "matches": matches}
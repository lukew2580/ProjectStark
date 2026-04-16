"""
Hardwareless AI — Security API Routes
Virus protection, sandboxing, threat detection
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/security", tags=["security"])


class ScanInputRequest(BaseModel):
    text: str


class SetPermissionsRequest(BaseModel):
    skill_name: str
    permissions: List[str]  # file_read, file_write, network, execute, shell, import


class ExecuteSkillRequest(BaseModel):
    skill_name: str
    code: str
    args: Dict[str, Any] = {}


@router.get("/status")
async def get_security_status():
    """Get security layer status."""
    from core_engine.security import get_security, get_sandbox
    
    security = get_security()
    sandbox = get_sandbox()
    
    return {
        "enabled": True,
        "rules_count": len(security._rules),
        "quarantined_count": len(security.get_quarantine()),
        "executions_count": sandbox._execution_count,
        "max_executions": sandbox._max_executions,
        "note": "Hardwareless AI security layer active"
    }


@router.post("/scan")
async def scan_input(request: ScanInputRequest):
    """Scan input for threats."""
    from core_engine.security import get_security
    
    security = get_security()
    report = security.scan_input(request.text)
    
    return {
        "level": report.level.value,
        "threat_type": report.threat_type,
        "description": report.description,
        "blocked": report.blocked,
        "recommendations": report.recommendations
    }


@router.post("/sanitize")
async def sanitize_input(request: ScanInputRequest):
    """Sanitize input by removing dangerous patterns."""
    from core_engine.security import get_security
    
    security = get_security()
    sanitized = security.sanitize_input(request.text)
    
    return {
        "original": request.text,
        "sanitized": sanitized
    }


@router.post("/permissions")
async def set_skill_permissions(request: SetPermissionsRequest):
    """Set permissions for a skill."""
    from core_engine.security import get_security, Permission
    
    security = get_security()
    
    perms = []
    for p in request.permissions:
        try:
            perms.append(Permission(p))
        except ValueError:
            pass
    
    security.set_skill_permissions(request.skill_name, perms)
    
    return {
        "status": "set",
        "skill": request.skill_name,
        "permissions": [p.value for p in perms]
    }


@router.get("/quarantine")
async def get_quarantine():
    """Get list of quarantined items."""
    from core_engine.security import get_security
    
    security = get_security()
    return {"quarantined": security.get_quarantine()}


@router.post("/quarantine/clear")
async def clear_quarantine():
    """Clear quarantine."""
    from core_engine.security import get_security
    
    security = get_security()
    security.clear_quarantine()
    
    return {"status": "cleared"}


@router.post("/sandbox/execute")
async def sandbox_execute(request: ExecuteSkillRequest):
    """Execute skill in sandbox."""
    from core_engine.security import get_sandbox
    
    sandbox = get_sandbox()
    result = await sandbox.execute_skill(request.skill_name, request.code, request.args)
    
    return {
        "result": result.result,
        "blocked_permissions": result.blocked_permissions,
        "execution_time": result.execution_time
    }


@router.get("/rules")
async def list_security_rules():
    """List all security rules."""
    from core_engine.security import get_security
    
    security = get_security()
    return {
        "rules": [
            {
                "name": r.name,
                "pattern": r.pattern,
                "level": r.threat_level.value,
                "description": r.description
            }
            for r in security._rules
        ]
    }
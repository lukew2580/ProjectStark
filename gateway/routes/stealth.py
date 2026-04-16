"""
Hardwareless AI — Stealth Mode API Routes
Hide defensive capabilities from attackers
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/stealth", tags=["stealth"])


class SetStealthLevelRequest(BaseModel):
    level: str  # visible, stealth, ghost


class ProbeRequest(BaseModel):
    probe_type: str
    source_ip: Optional[str] = None
    request: Optional[str] = None


class CheckTrapRequest(BaseModel):
    path: str


@router.get("/status")
async def get_stealth_status():
    """Get stealth mode status."""
    from core_engine.stealth import get_stealth, get_decoy, get_anti_recon
    
    stealth = get_stealth()
    decoy = get_decoy()
    anti_recon = get_anti_recon()
    
    return {
        "stealth_level": stealth._level.value,
        "decoy_traps": len(decoy._honeypots),
        "probes_detected": anti_recon.get_probe_count(),
        "note": "Defensive capabilities hidden from attackers"
    }


@router.post("/level")
async def set_stealth_level(request: SetStealthLevelRequest):
    """Set stealth level."""
    from core_engine.stealth import get_stealth, ObfuscationLevel
    
    stealth = get_stealth()
    
    try:
        level = ObfuscationLevel(request.level)
        stealth.set_level(level)
        return {"status": "set", "level": level.value}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid level")


@router.post("/probe")
async def respond_to_probe(request: ProbeRequest):
    """Respond to reconnaissance probe with fake data."""
    from core_engine.stealth import get_stealth
    
    stealth = get_stealth()
    response = stealth.respond_to_probe(request.probe_type)
    
    return response


@router.post("/scan/obfuscate")
async def obfuscate_scan_results(actual_result: Dict):
    """Obfuscate scan results to hide detection."""
    from core_engine.stealth import get_stealth
    
    stealth = get_stealth()
    fake_result = stealth.fake_scan_result(actual_result)
    
    return fake_result


@router.post("/decoy/check")
async def check_decoy_trap(request: CheckTrapRequest):
    """Check if path is a decoy trap."""
    from core_engine.stealth import get_decoy
    
    decoy = get_decoy()
    is_trap = decoy.check_trap(request.path)
    
    return {
        "path": request.path,
        "is_trap": is_trap,
        "response": decoy.get_decoy_response(request.path) if is_trap else None
    }


@router.post("/anti-recon/analyze")
async def analyze_probe(request: ProbeRequest):
    """Analyze if request is reconnaissance."""
    from core_engine.stealth import get_anti_recon
    
    anti_recon = get_anti_recon()
    result = anti_recon.analyze_probe(
        request.source_ip or "unknown",
        request.request or ""
    )
    
    return result


@router.get("/anti-recon/stats")
async def get_anti_recon_stats():
    """Get anti-reconnaissance statistics."""
    from core_engine.stealth import get_anti_recon
    
    anti_recon = get_anti_recon()
    return {
        "total_probes": anti_recon.get_probe_count()
    }


@router.get("/levels")
async def get_stealth_levels():
    """Get available stealth levels."""
    return {
        "levels": [
            {"id": "visible", "description": "Full transparency for legitimate users"},
            {"id": "stealth", "description": "Partial obfuscation, basic protection"},
            {"id": "ghost", "description": "Full invisibility, appears as basic utility"}
        ]
    }
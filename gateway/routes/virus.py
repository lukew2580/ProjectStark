"""
Hardwareless AI — Virus Guard API Routes
VIRUS-VDI: Detection & Eradication System
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import base64

router = APIRouter(prefix="/v1/virus", tags=["virus"])


class ScanDataRequest(BaseModel):
    data: str  # Base64 encoded data


class ScanFileRequest(BaseModel):
    file_path: str


class ScanBehaviorRequest(BaseModel):
    behavior: str


class EradicateRequest(BaseModel):
    virus_name: str
    target: str


class AddSignatureRequest(BaseModel):
    name: str
    category: str  # ransomware, trojan, worm, virus, rootkit, spyware, botnet
    keywords: List[str]
    threat_level: str  # safe, low, medium, high, critical


@router.get("/status")
async def get_virus_status():
    """Get virus detection system status."""
    from core_engine.virus_guard import get_virus_detector
    
    detector = get_virus_detector()
    stats = detector.get_statistics()
    
    return {
        "system": "VIRUS-VDI",
        "name": "Virus Detection & Eradication",
        "status": "active",
        **stats
    }


@router.post("/scan/data")
async def scan_data(request: ScanDataRequest):
    """Scan data for viruses using HDC similarity."""
    from core_engine.virus_guard import get_virus_detector
    
    detector = get_virus_detector()
    
    try:
        data = base64.b64decode(request.data)
        report = await detector.scan_data(data)
        
        return {
            "status": report.status.value,
            "virus_name": report.virus_name,
            "category": report.category.value,
            "confidence": report.confidence,
            "actions": report.actions_taken,
            "similarity": report.vector_similarity
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scan/file")
async def scan_file(request: ScanFileRequest):
    """Scan a file for viruses."""
    from core_engine.virus_guard import get_virus_detector
    
    detector = get_virus_detector()
    report = await detector.scan_file(request.file_path)
    
    return {
        "file": request.file_path,
        "status": report.status.value,
        "virus_name": report.virus_name,
        "category": report.category.value,
        "confidence": report.confidence,
        "actions": report.actions_taken
    }


@router.post("/scan/behavior")
async def scan_behavior(request: ScanBehaviorRequest):
    """Scan for virus-like behavior patterns."""
    from core_engine.virus_guard import get_virus_detector
    
    detector = get_virus_detector()
    report = await detector.detect_behavior(request.behavior)
    
    return {
        "behavior": request.behavior,
        "status": report.status.value,
        "virus_name": report.virus_name,
        "category": report.category.value,
        "confidence": report.confidence,
        "actions": report.actions_taken
    }


@router.post("/eradicate")
async def eradicate_virus(request: EradicateRequest):
    """Eradicate a detected virus."""
    from core_engine.virus_guard import get_virus_eradicator
    
    eradicator = get_virus_eradicator()
    action = await eradicator.eradicate(request.virus_name, request.target)
    
    return {
        "action": action.action_type,
        "target": action.target,
        "description": action.description,
        "success": action.success
    }


@router.post("/patch")
async def patch_vulnerability(vuln_type: str):
    """Apply patch for known vulnerability."""
    from core_engine.virus_guard import get_virus_eradicator
    
    eradicator = get_virus_eradicator()
    action = await eradicator.patch_vulnerability(vuln_type)
    
    return {
        "vulnerability": vuln_type,
        "status": "patched" if action.success else "failed"
    }


@router.get("/quarantine")
async def get_quarantine():
    """Get quarantined items."""
    from core_engine.virus_guard import get_virus_detector
    
    detector = get_virus_detector()
    return {"quarantined": detector.get_quarantine()}


@router.get("/history")
async def get_detection_history(limit: int = 100):
    """Get detection history."""
    from core_engine.virus_guard import get_virus_detector
    
    detector = get_virus_detector()
    return {"history": detector.get_detection_history(limit)}


@router.get("/signatures")
async def list_signatures():
    """List known virus signatures."""
    from core_engine.virus_guard import get_virus_detector
    
    detector = get_virus_detector()
    return {
        "signatures": [
            {
                "name": sig.name,
                "category": sig.category.value,
                "threat_level": sig.threat_level.value,
                "variants": sig.variants,
                "first_seen": sig.first_seen
            }
            for sig in detector.signatures.values()
        ]
    }


@router.post("/signatures/add")
async def add_signature(request: AddSignatureRequest):
    """Add a new virus signature."""
    from core_engine.virus_guard import get_virus_detector, VirusCategory, ThreatLevel
    
    detector = get_virus_detector()
    
    try:
        category = VirusCategory(request.category)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    try:
        level = ThreatLevel(request.threat_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid threat level")
    
    detector._create_signature(request.name, category, request.keywords, level)
    
    return {
        "status": "added",
        "name": request.name,
        "category": request.category,
        "threat_level": request.threat_level
    }


@router.get("/stats")
async def get_statistics():
    """Get detection statistics."""
    from core_engine.virus_guard import get_virus_detector
    
    detector = get_virus_detector()
    return detector.get_statistics()
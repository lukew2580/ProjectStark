"""
Hardwareless AI — Antivirus API Routes
Multi-engine antivirus scanning integration
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/antivirus", tags=["antivirus"])


class ScanFileRequest(BaseModel):
    file_path: str


class ScanDirectoryRequest(BaseModel):
    directory: str
    recursive: bool = True


class MultiEngineScanRequest(BaseModel):
    file_path: str
    engines: Optional[List[str]] = None


@router.get("/status")
async def get_av_status():
    """Get antivirus integration status."""
    from core_engine.antivirus_integration import get_antivirus_integration
    
    av = get_antivirus_integration()
    engines = av.get_available_engines()
    
    return {
        "system": "Antivirus Integration Layer",
        "status": "active",
        "engines_available": engines,
        "total_engines": len(engines)
    }


@router.get("/engines")
async def list_engines():
    """List all antivirus engines and their status."""
    from core_engine.antivirus_integration import get_antivirus_integration, AntivirusEngine
    
    av = get_antivirus_integration()
    status_list = av.get_engine_status()
    
    return {
        "engines": [
            {
                "engine": s.engine.value,
                "available": s.available,
                "version": s.version,
                "last_update": s.last_update,
                "signatures": s.signatures_count
            }
            for s in status_list
        ]
    }


@router.post("/scan/single")
async def scan_single_file(request: ScanFileRequest):
    """Scan a single file with available engines."""
    from core_engine.antivirus_integration import get_antivirus_integration
    
    av = get_antivirus_integration()
    results = await av.scan_multi_engine(request.file_path)
    
    infected = any(r.is_infected for r in results)
    
    return {
        "file": request.file_path,
        "scanned": True,
        "infected": infected,
        "results": [
            {
                "engine": r.engine,
                "infected": r.is_infected,
                "virus": r.virus_name,
                "scan_time_ms": r.scan_time_ms
            }
            for r in results
        ]
    }


@router.post("/scan/multi")
async def scan_multi_engine(request: MultiEngineScanRequest):
    """Scan with specific engines."""
    from core_engine.antivirus_integration import get_antivirus_integration, AntivirusEngine
    
    av = get_antivirus_integration()
    
    engines = None
    if request.engines:
        engines = [AntivirusEngine(e) for e in request.engines]
    
    results = await av.scan_multi_engine(request.file_path, engines)
    
    return {
        "file": request.file_path,
        "results": [
            {
                "engine": r.engine,
                "infected": r.is_infected,
                "virus": r.virus_name,
                "scan_time_ms": r.scan_time_ms
            }
            for r in results
        ]
    }


@router.post("/scan/directory")
async def scan_directory(request: ScanDirectoryRequest):
    """Scan an entire directory."""
    from core_engine.antivirus_integration import get_antivirus_integration
    
    av = get_antivirus_integration()
    result = await av.scan_directory(request.directory, request.recursive)
    
    return result


@router.post("/quarantine")
async def quarantine_file(file_path: str):
    """Move file to quarantine."""
    from core_engine.antivirus_integration import get_antivirus_integration
    
    av = get_antivirus_integration()
    quarantined_path = await av.quarantine_file(file_path)
    
    return {
        "file": file_path,
        "quarantined": quarantined_path,
        "success": bool(quarantined_path)
    }


@router.get("/history")
async def get_scan_history(limit: int = 100):
    """Get scan history."""
    from core_engine.antivirus_integration import get_antivirus_integration
    
    av = get_antivirus_integration()
    return {"history": av.get_scan_history(limit)}
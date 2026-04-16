"""
Hardwareless AI — Scanner API Routes
Real-time and scheduled scanning
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/scanner", tags=["scanner"])


class AddScheduledScanRequest(BaseModel):
    scan_id: str
    schedule: str  # hourly, daily, weekly, manual
    target_paths: List[str]
    recursive: bool = True


class RunScanRequest(BaseModel):
    target_path: str
    recursive: bool = False


class WatchDirectoryRequest(BaseModel):
    directory: str


@router.get("/status")
async def get_scanner_status():
    """Get automated scanner status."""
    from core_engine.automated_scanner import get_automated_scanner
    
    scanner = get_automated_scanner()
    scans = scanner.get_scheduled_scans()
    
    return {
        "system": "Automated Scanner Daemon",
        "status": "active",
        "scheduled_scans": len(scans),
        "daemon_running": True
    }


@router.get("/scheduled")
async def get_scheduled_scans():
    """Get all scheduled scans."""
    from core_engine.automated_scanner import get_automated_scanner
    
    scanner = get_automated_scanner()
    return {"scans": scanner.get_scheduled_scans()}


@router.post("/scheduled/add")
async def add_scheduled_scan(request: AddScheduledScanRequest):
    """Add a new scheduled scan."""
    from core_engine.automated_scanner import get_automated_scanner, ScanSchedule
    
    scanner = get_automated_scanner()
    
    try:
        schedule = ScanSchedule(request.schedule)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule")
    
    scanner.add_scheduled_scan(
        request.scan_id,
        schedule,
        request.target_paths,
        request.recursive
    )
    
    return {
        "status": "added",
        "scan_id": request.scan_id,
        "schedule": request.schedule,
        "targets": request.target_paths
    }


@router.delete("/scheduled/{scan_id}")
async def remove_scheduled_scan(scan_id: str):
    """Remove a scheduled scan."""
    from core_engine.automated_scanner import get_automated_scanner
    
    scanner = get_automated_scanner()
    scanner.remove_scheduled_scan(scan_id)
    
    return {"status": "removed", "scan_id": scan_id}


@router.post("/run")
async def run_scan(request: RunScanRequest):
    """Run a manual scan."""
    from core_engine.automated_scanner import get_automated_scanner
    
    scanner = get_automated_scanner()
    
    from core_engine.automated_scanner import ScheduledScan, ScanSchedule
    
    scan = ScheduledScan(
        scan_id="manual_scan",
        schedule=ScanSchedule.MANUAL,
        target_paths=[request.target_path],
        recursive=request.recursive
    )
    
    report = await scanner.run_scan(scan)
    
    return {
        "scan_id": report.scan_id,
        "target": report.target,
        "files_scanned": report.files_scanned,
        "threats_found": report.threats_found,
        "quarantined": report.quarantined,
        "duration_seconds": report.duration_seconds,
        "timestamp": report.timestamp
    }


@router.post("/run/scheduled")
async def run_scheduled_scan_now(scan_id: str):
    """Run a scheduled scan immediately."""
    from core_engine.automated_scanner import get_automated_scanner
    
    scanner = get_automated_scanner()
    scans = scanner.get_scheduled_scans()
    
    scan = next((s for s in scans if s["scan_id"] == scan_id), None)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return {"status": "queued", "scan_id": scan_id}


@router.post("/watch")
async def watch_directory(request: WatchDirectoryRequest):
    """Add directory to watch list."""
    from core_engine.automated_scanner import get_automated_scanner
    
    scanner = get_automated_scanner()
    scanner.watch_directory(request.directory)
    
    return {
        "status": "watching",
        "directory": request.directory
    }


@router.post("/start_daemon")
async def start_daemon():
    """Start the scanning daemon."""
    from core_engine.automated_scanner import get_automated_scanner
    
    scanner = get_automated_scanner()
    scanner.start_daemon()
    
    return {"status": "daemon_started"}


@router.post("/stop_daemon")
async def stop_daemon():
    """Stop the scanning daemon."""
    from core_engine.automated_scanner import get_automated_scanner
    
    scanner = get_automated_scanner()
    scanner.stop_daemon()
    
    return {"status": "daemon_stopped"}


@router.get("/history")
async def get_scan_history(limit: int = 100):
    """Get scan history."""
    from core_engine.automated_scanner import get_automated_scanner
    
    scanner = get_automated_scanner()
    return {"history": scanner.get_scan_history(limit)}
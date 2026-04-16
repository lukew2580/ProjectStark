"""
Hardwareless AI — Automated Scanner Daemon
Real-time and scheduled scanning
"""
import asyncio
import time
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import os

from core_engine.antivirus_integration import get_antivirus_integration
from core_engine.virus_guard import get_virus_detector


class ScanSchedule(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    ON_ACCESS = "on_access"
    MANUAL = "manual"


@dataclass
class ScheduledScan:
    scan_id: str
    schedule: ScanSchedule
    target_paths: List[str]
    recursive: bool = True
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    results: Dict = field(default_factory=dict)


@dataclass
class ScanReport:
    scan_id: str
    scan_type: str
    target: str
    files_scanned: int
    threats_found: int
    quarantined: int
    duration_seconds: float
    timestamp: str


class AutomatedScanner:
    """
    Real-time and scheduled scanning daemon.
    Monitors directories and runs scans on schedule.
    """
    
    def __init__(self):
        self._scheduled_scans: Dict[str, ScheduledScan] = {}
        self._scan_results: List[ScanReport] = []
        self._watch_directories: Dict[str, Any] = {}
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None
        self._callback: Optional[Callable] = None
        self._init_default_scans()
    
    def _init_default_scans(self):
        """Initialize default scheduled scans."""
        user_downloads = os.path.expanduser("~/Downloads")
        user_documents = os.path.expanduser("~/Documents")
        
        self._scheduled_scans["daily_downloads"] = ScheduledScan(
            scan_id="daily_downloads",
            schedule=ScanSchedule.DAILY,
            target_paths=[user_downloads],
            recursive=True,
            next_run=self._calc_next_run(ScanSchedule.DAILY)
        )
        
        self._scheduled_scans["weekly_full"] = ScheduledScan(
            scan_id="weekly_full",
            schedule=ScanSchedule.WEEKLY,
            target_paths=[user_documents, user_downloads],
            recursive=True,
            next_run=self._calc_next_run(ScanSchedule.WEEKLY)
        )
    
    def _calc_next_run(self, schedule: ScanSchedule) -> str:
        """Calculate next run time."""
        now = datetime.now()
        
        if schedule == ScanSchedule.HOURLY:
            next_time = now + timedelta(hours=1)
        elif schedule == ScanSchedule.DAILY:
            next_time = now + timedelta(days=1)
        elif schedule == ScanSchedule.WEEKLY:
            next_time = now + timedelta(weeks=1)
        else:
            next_time = now + timedelta(days=1)
        
        return next_time.isoformat()
    
    def add_scheduled_scan(
        self,
        scan_id: str,
        schedule: ScanSchedule,
        target_paths: List[str],
        recursive: bool = True
    ):
        """Add a scheduled scan."""
        scan = ScheduledScan(
            scan_id=scan_id,
            schedule=schedule,
            target_paths=target_paths,
            recursive=recursive,
            next_run=self._calc_next_run(schedule)
        )
        self._scheduled_scans[scan_id] = scan
    
    def remove_scheduled_scan(self, scan_id: str):
        """Remove a scheduled scan."""
        if scan_id in self._scheduled_scans:
            del self._scheduled_scans[scan_id]
    
    def get_scheduled_scans(self) -> List[Dict]:
        """Get all scheduled scans."""
        return [
            {
                "scan_id": s.scan_id,
                "schedule": s.schedule.value,
                "target_paths": s.target_paths,
                "recursive": s.recursive,
                "enabled": s.enabled,
                "last_run": s.last_run,
                "next_run": s.next_run
            }
            for s in self._scheduled_scans.values()
        ]
    
    async def run_scan(self, scan: ScheduledScan) -> ScanReport:
        """Run a scheduled scan."""
        start_time = time.time()
        scan_id = f"{scan.scan_id}_{int(start_time)}"
        
        av = get_antivirus_integration()
        detector = get_virus_detector()
        
        total_scanned = 0
        threats_found = 0
        quarantined = 0
        
        for target_path in scan.target_paths:
            if os.path.isdir(target_path):
                result = await av.scan_directory(target_path, scan.recursive)
                total_scanned += result["scanned"]
                threats_found += result["infected"]
                
                for infected in result.get("infected_files", []):
                    quarantined += 1
            elif os.path.isfile(target_path):
                results = await av.scan_multi_engine(target_path)
                if any(r.is_infected for r in results):
                    threats_found += 1
                    await av.quarantine_file(target_path)
                    quarantined += 1
                total_scanned += 1
        
        report = ScanReport(
            scan_id=scan_id,
            scan_type=scan.schedule.value,
            target=", ".join(scan.target_paths),
            files_scanned=total_scanned,
            threats_found=threats_found,
            quarantined=quarantined,
            duration_seconds=time.time() - start_time,
            timestamp=datetime.now().isoformat()
        )
        
        self._scan_results.append(report)
        scan.last_run = report.timestamp
        scan.next_run = self._calc_next_run(scan.schedule)
        
        return report
    
    async def start_daemon(self):
        """Start the scanning daemon."""
        self._running = True
        
        while self._running:
            now = datetime.now()
            
            for scan in self._scheduled_scans.values():
                if not scan.enabled:
                    continue
                
                if scan.next_run:
                    next_run = datetime.fromisoformat(scan.schedule)
                    if now >= next_run:
                        await self.run_scan(scan)
            
            await asyncio.sleep(60)
    
    def stop_daemon(self):
        """Stop the scanning daemon."""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
    
    def set_callback(self, callback: Callable):
        """Set callback for scan completion."""
        self._callback = callback
    
    async def scan_and_notify(self, file_path: str) -> Dict:
        """Scan file and notify callback."""
        av = get_antivirus_integration()
        results = await av.scan_multi_engine(file_path)
        
        infected = any(r.is_infected for r in results)
        
        if infected and self._callback:
            await self._callback({
                "file": file_path,
                "infected": infected,
                "results": [{"engine": r.engine, "virus": r.virus_name} for r in results]
            })
        
        return {
            "file": file_path,
            "infected": infected,
            "results": [
                {"engine": r.engine, "virus": r.virus_name}
                for r in results
            ]
        }
    
    def get_scan_history(self, limit: int = 100) -> List[Dict]:
        """Get scan history."""
        return [
            {
                "scan_id": r.scan_id,
                "scan_type": r.scan_type,
                "target": r.target,
                "files_scanned": r.files_scanned,
                "threats_found": r.threats_found,
                "quarantined": r.quarantined,
                "duration_seconds": r.duration_seconds,
                "timestamp": r.timestamp
            }
            for r in self._scan_results[-limit:]
        ]
    
    def watch_directory(self, directory: str):
        """Add directory to watch list."""
        if directory not in self._watch_directories:
            self._watch_directories[directory] = {
                "path": directory,
                "files_checked": []
            }


_global_scanner: Optional[AutomatedScanner] = None


def get_automated_scanner() -> AutomatedScanner:
    global _global_scanner
    if _global_scanner is None:
        _global_scanner = AutomatedScanner()
    return _global_scanner
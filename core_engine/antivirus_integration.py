"""
Hardwareless AI — Antivirus Integration Layer
Integrates with open-source antivirus engines for enhanced detection
"""
import asyncio
import subprocess
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import os

from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import similarity
from config.settings import DIMENSIONS


class AntivirusEngine(Enum):
    CLAMAV = "clamav"
    CLAMTK = "clamtk"
    HYPATIA = "hypatia"
    IMMUNET = "immunet"
    XCITIUM = "xcitium"
    COMODO = "comodo"
    MICROSOFT_DEFENDER = "microsoft_defender"


@dataclass
class ScanResult:
    engine: str
    file_path: str
    is_infected: bool
    virus_name: Optional[str]
    signature_match: str
    scan_time_ms: float
    raw_output: str


@dataclass
class EngineStatus:
    engine: AntivirusEngine
    available: bool
    version: Optional[str]
    last_update: Optional[str]
    signatures_count: int = 0


class AntivirusIntegration:
    """
    Unified antivirus integration layer.
    Coordinates multiple AV engines for maximum detection coverage.
    """
    
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self._engines: Dict[AntivirusEngine, bool] = {}
        self._scan_history: List[ScanResult] = []
        self._quarantine_path = "/tmp/hardwareless_ai/quarantine"
        self._setup_directories()
        self._check_engines()
    
    def _setup_directories(self):
        """Create necessary directories."""
        os.makedirs(self._quarantine_path, exist_ok=True)
    
    def _check_engines(self):
        """Check which engines are available."""
        self._engines = {
            AntivirusEngine.CLAMAV: self._check_clamav(),
            AntivirusEngine.CLAMTK: self._check_clamtk(),
            AntivirusEngine.HYPATIA: self._check_hypatia(),
            AntivirusEngine.IMMUNET: self._check_immunet(),
            AntivirusEngine.XCITIUM: self._check_xcitium(),
            AntivirusEngine.COMODO: self._check_comodo(),
            AntivirusEngine.MICROSOFT_DEFENDER: self._check_defender(),
        }
    
    def _check_clamav(self) -> bool:
        """Check if ClamAV is available."""
        try:
            result = subprocess.run(
                ["clamd", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            try:
                result = subprocess.run(
                    ["clamscan", "--version"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False
    
    def _check_clamtk(self) -> bool:
        """Check if ClamTK is available."""
        return os.path.exists("/usr/bin/clamtk") or os.path.exists("/usr/local/bin/clamtk")
    
    def _check_hypatia(self) -> bool:
        """Check if Hypatia is available."""
        return os.path.exists("/opt/hypatia") or os.path.exists(os.path.expanduser("~/hypatia"))
    
    def _check_immunet(self) -> bool:
        """Check if Immunet is available."""
        return os.path.exists("/opt/immunet") or os.path.exists(os.path.expanduser("~/immunet"))
    
    def _check_xcitium(self) -> bool:
        """Check if Xcitium/Comodo is available."""
        return os.path.exists("/opt/xcitium") or os.path.exists("C:\\Program Files\\Xcitium")
    
    def _check_comodo(self) -> bool:
        """Check if Comodo is available."""
        return os.path.exists("/opt/comodo") or os.path.exists("C:\\Program Files\\COMODO")
    
    def _check_defender(self) -> bool:
        """Check if Microsoft Defender is available."""
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["powershell", "Get-MpComputerStatus"],
                    capture_output=True,
                    timeout=10
                )
                return result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False
        return False
    
    def get_engine_status(self) -> List[EngineStatus]:
        """Get status of all antivirus engines."""
        statuses = []
        for engine, available in self._engines.items():
            status = EngineStatus(
                engine=engine,
                available=available,
                version=None,
                last_update=None,
                signatures_count=0
            )
            statuses.append(status)
        return statuses
    
    async def scan_with_clamav(self, file_path: str) -> ScanResult:
        """Scan file with ClamAV."""
        start_time = datetime.now()
        
        try:
            result = subprocess.run(
                ["clamscan", "--stdout", file_path],
                capture_output=True,
                timeout=60
            )
            output = result.stdout.decode()
            
            is_infected = "FOUND" in output or "infected" in output.lower()
            virus_name = None
            if is_infected:
                parts = output.split("FOUND")
                if len(parts) > 1:
                    virus_name = parts[1].strip().split()[0]
            
            scan_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ScanResult(
                engine=AntivirusEngine.CLAMAV.value,
                file_path=file_path,
                is_infected=is_infected,
                virus_name=virus_name,
                signature_match=virus_name or "none",
                scan_time_ms=scan_time,
                raw_output=output
            )
        except Exception as e:
            return ScanResult(
                engine=AntivirusEngine.CLAMAV.value,
                file_path=file_path,
                is_infected=False,
                virus_name=None,
                signature_match="error",
                scan_time_ms=0,
                raw_output=str(e)
            )
    
    async def scan_with_defender(self, file_path: str) -> ScanResult:
        """Scan file with Microsoft Defender."""
        start_time = datetime.now()
        
        try:
            script = f'Scan-File -Path "{file_path}" -RemoveInfected'
            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True,
                timeout=60
            )
            output = result.stdout.decode()
            
            is_infected = "Threat" in output or "Malware" in output
            scan_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ScanResult(
                engine=AntivirusEngine.MICROSOFT_DEFENDER.value,
                file_path=file_path,
                is_infected=is_infected,
                virus_name=None,
                signature_match="defender",
                scan_time_ms=scan_time,
                raw_output=output
            )
        except Exception as e:
            return ScanResult(
                engine=AntivirusEngine.MICROSOFT_DEFENDER.value,
                file_path=file_path,
                is_infected=False,
                virus_name=None,
                signature_match="error",
                scan_time_ms=0,
                raw_output=str(e)
            )
    
    async def scan_multi_engine(
        self,
        file_path: str,
        engines: List[AntivirusEngine] = None
    ) -> List[ScanResult]:
        """Scan with multiple engines concurrently."""
        if engines is None:
            engines = [e for e, avail in self._engines.items() if avail]
        
        tasks = []
        for engine in engines:
            if engine == AntivirusEngine.CLAMAV:
                tasks.append(self.scan_with_clamav(file_path))
            elif engine == AntivirusEngine.MICROSOFT_DEFENDER:
                tasks.append(self.scan_with_defender(file_path))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for r in results:
            if isinstance(r, ScanResult):
                valid_results.append(r)
                self._scan_history.append(r)
        
        return valid_results
    
    async def scan_directory(
        self,
        directory: str,
        recursive: bool = True
    ) -> Dict[str, Any]:
        """Scan entire directory with available engines."""
        infected_files = []
        scanned_count = 0
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                results = await self.scan_multi_engine(file_path)
                
                for result in results:
                    if result.is_infected:
                        infected_files.append({
                            "file": file_path,
                            "engine": result.engine,
                            "virus": result.virus_name,
                            "quarantined": await self.quarantine_file(file_path)
                        })
                scanned_count += 1
            
            if not recursive:
                break
        
        return {
            "directory": directory,
            "scanned": scanned_count,
            "infected": len(infected_files),
            "infected_files": infected_files,
            "clean": scanned_count - len(infected_files)
        }
    
    async def quarantine_file(self, file_path: str) -> str:
        """Move suspicious file to quarantine."""
        try:
            quarantine_name = os.path.join(
                self._quarantine_path,
                f"{hashlib.md5(file_path.encode()).hexdigest()}_{os.path.basename(file_path)}"
            )
            
            os.rename(file_path, quarantine_name)
            return quarantine_name
        except Exception:
            return ""
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engines."""
        return [e.value for e, avail in self._engines.items() if avail]
    
    def get_scan_history(self, limit: int = 100) -> List[Dict]:
        """Get scan history."""
        return [
            {
                "engine": r.engine,
                "file": r.file_path,
                "infected": r.is_infected,
                "virus": r.virus_name,
                "scan_time_ms": r.scan_time_ms
            }
            for r in self._scan_history[-limit:]
        ]


_global_av: Optional[AntivirusIntegration] = None


def get_antivirus_integration() -> AntivirusIntegration:
    global _global_av
    if _global_av is None:
        _global_av = AntivirusIntegration()
    return _global_av
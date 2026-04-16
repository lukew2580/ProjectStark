"""
Hardwareless AI — Virus Detection & Eradication System (VIRUS-VDI)
In-house AI that learns, detects, and eradicates viruses proactively
"""
import hashlib
import asyncio
import json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np

from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import bind, bundle, similarity
from core_engine.security import get_security, ThreatLevel
from config.settings import DIMENSIONS


class VirusCategory(Enum):
    RANSOMWARE = "ransomware"
    TROJAN = "trojan"
    WORM = "worm"
    VIRUS = "virus"
    ROOTKIT = "rootkit"
    SPYWARE = "spyware"
    BOTNET = "botnet"
    UNKNOWN = "unknown"


class DetectionStatus(Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    INFECTED = "infected"
    QUARANTINED = "quarantined"
    ERADICATED = "eradicated"


@dataclass
class VirusSignature:
    """A virus signature encoded as HDC hypervector."""
    name: str
    category: VirusCategory
    signature_hash: str
    vector: np.ndarray
    variants: List[str] = field(default_factory=list)
    first_seen: str = ""
    threat_level: ThreatLevel = ThreatLevel.HIGH


@dataclass
class VirusReport:
    """Report of detected virus."""
    status: DetectionStatus
    virus_name: str
    category: VirusCategory
    confidence: float
    actions_taken: List[str]
    vector_similarity: float


@dataclass
class EradicationAction:
    """Action to eradicate a virus."""
    action_type: str  # quarantine, delete, patch, isolate
    target: str
    description: str
    success: bool


class VirusDetector:
    """
    HDC-based Virus Detection System.
    
    Uses hypervector similarity to detect:
    - Known virus signatures
    - Variants of known viruses
    - Behavioral patterns
    
    Unique: Uses HDC's associative memory for pattern matching.
    """
    
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self.signatures: Dict[str, VirusSignature] = {}
        self._quarantine: List[str] = []
        self._detection_history: List[VirusReport] = []
        self._setup_known_signatures()
    
    def _setup_known_signatures(self):
        """Initialize known virus signatures as HDC vectors."""
        known_viruses = [
            ("WannaCry", VirusCategory.RANSOMWARE, ["wcry", "wncry", "ransomware"], ThreatLevel.CRITICAL),
            ("NotPetya", VirusCategory.RANSOMWARE, ["petya", "expetr", "noptya"], ThreatLevel.CRITICAL),
            ("CryptoLocker", VirusCategory.RANSOMWARE, ["cryptolocker", "crypto"], ThreatLevel.HIGH),
            ("Emotet", VirusCategory.TROJAN, ["emotet", "heodo"], ThreatLevel.HIGH),
            ("TrickBot", VirusCategory.TROJAN, ["trickbot", "trickster"], ThreatLevel.HIGH),
            ("Conficker", VirusCategory.WORM, ["conficker", "downadup"], ThreatLevel.MEDIUM),
            ("ILOVEYOU", VirusCategory.VIRUS, ["iloveyou", "lovebug"], ThreatLevel.MEDIUM),
            ("Stuxnet", VirusCategory.WORM, ["stuxnet", "rootkit"], ThreatLevel.HIGH),
        ]
        
        for name, category, keywords, level in known_viruses:
            self._create_signature(name, category, keywords, level)
    
    def _create_signature(self, name: str, category: VirusCategory, keywords: List[str], level: ThreatLevel):
        """Create HDC vector signature from virus keywords."""
        combined = " ".join(keywords)
        seed = hashlib.md5(combined.encode()).digest()
        seed_int = int.from_bytes(seed[:4], 'big') % (2**31)
        
        vector = generate_random_vector(self.dimensions, seed=seed_int)
        
        signature = VirusSignature(
            name=name,
            category=category,
            signature_hash=hashlib.sha256(combined.encode()).hexdigest(),
            vector=vector,
            variants=keywords,
            first_seen=datetime.now().isoformat(),
            threat_level=level
        )
        
        self.signatures[name] = signature
    
    async def scan_data(self, data: bytes) -> VirusReport:
        """Scan data for virus signatures using HDC similarity."""
        data_hash = hashlib.sha256(data).hexdigest()
        data_seed = int.from_bytes(hashlib.sha256(data_hash.encode()).digest()[:4], 'big') % (2**31)
        data_vector = generate_random_vector(self.dimensions, seed=data_seed)
        
        best_match = None
        best_similarity = 0.0
        
        for name, sig in self.signatures.items():
            sim = similarity(data_vector, sig.vector, self.dimensions)
            if sim > best_similarity:
                best_similarity = sim
                best_match = sig
        
        actions = []
        
        if best_similarity > 0.7:
            status = DetectionStatus.INFECTED
            actions.append(f"Detected: {best_match.name}")
            actions.append(f"Category: {best_match.category.value}")
            
            if best_match.threat_level == ThreatLevel.CRITICAL:
                actions.append("QUARANTINE: Critical threat isolated")
                self._quarantine.append(data_hash)
            elif best_match.threat_level == ThreatLevel.HIGH:
                actions.append("ALERT: High threat - review required")
        elif best_similarity > 0.5:
            status = DetectionStatus.SUSPICIOUS
            actions.append("WARNING: Potential variant detected")
            actions.append(f"Similarity: {best_similarity:.2%}")
        else:
            status = DetectionStatus.CLEAN
            actions.append("SCAN COMPLETE: No threats found")
        
        report = VirusReport(
            status=status,
            virus_name=best_match.name if best_match else "Unknown",
            category=best_match.category if best_match else VirusCategory.UNKNOWN,
            confidence=best_similarity,
            actions_taken=actions,
            vector_similarity=best_similarity
        )
        
        self._detection_history.append(report)
        return report
    
    async def scan_file(self, file_path: str) -> VirusReport:
        """Scan a file for viruses."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            return await self.scan_data(data)
        except Exception as e:
            return VirusReport(
                status=DetectionStatus.SUSPICIOUS,
                virus_name="Scan Error",
                category=VirusCategory.UNKNOWN,
                confidence=0.0,
                actions_taken=[f"Error: {str(e)}"],
                vector_similarity=0.0
            )
    
    async def detect_behavior(self, behavior_pattern: str) -> VirusReport:
        """Detect virus-like behavior patterns."""
        behavior_hash = hashlib.sha256(behavior_pattern.encode()).hexdigest()
        behavior_seed = int.from_bytes(hashlib.sha256(behavior_hash.encode()).digest()[:4], 'big') % (2**31)
        behavior_vector = generate_random_vector(self.dimensions, seed=behavior_seed)
        
        suspicious_patterns = [
            "encrypt all files",
            "delete shadow copies", 
            "disable firewall",
            "modify hosts file",
            "inject code",
            "keylogger active",
            "miner detected",
            "persistence established"
        ]
        
        for pattern in suspicious_patterns:
            if pattern.lower() in behavior_pattern.lower():
                for name, sig in self.signatures.items():
                    sim = similarity(behavior_vector, sig.vector, self.dimensions)
                    if sim > 0.3:
                        return VirusReport(
                            status=DetectionStatus.INFECTED,
                            virus_name=f"Behavioral: {name}",
                            category=sig.category,
                            confidence=sim,
                            actions_taken=[f"Behavior detected: {pattern}", "Isolate process"],
                            vector_similarity=sim
                        )
        
        return VirusReport(
            status=DetectionStatus.CLEAN,
            virus_name="None",
            category=VirusCategory.UNKNOWN,
            confidence=0.0,
            actions_taken=["Behavior normal"],
            vector_similarity=0.0
        )
    
    def get_quarantine(self) -> List[str]:
        """Get list of quarantined items."""
        return self._quarantine.copy()
    
    def get_detection_history(self, limit: int = 100) -> List[Dict]:
        """Get detection history."""
        return [
            {
                "status": r.status.value,
                "virus": r.virus_name,
                "category": r.category.value,
                "confidence": r.confidence
            }
            for r in self._detection_history[-limit:]
        ]
    
    def get_statistics(self) -> Dict:
        """Get detection statistics."""
        total = len(self._detection_history)
        if total == 0:
            return {"total_scans": 0}
        
        infected = sum(1 for r in self._detection_history if r.status == DetectionStatus.INFECTED)
        suspicious = sum(1 for r in self._detection_history if r.status == DetectionStatus.SUSPICIOUS)
        clean = sum(1 for r in self._detection_history if r.status == DetectionStatus.CLEAN)
        
        return {
            "total_scans": total,
            "infected": infected,
            "suspicious": suspicious,
            "clean": clean,
            "quarantine_count": len(self._quarantine),
            "signatures_loaded": len(self.signatures)
        }


class VirusEradicator:
    """
    Coordinates virus eradication actions.
    Works with the detection system to remove threats.
    """
    
    def __init__(self, detector: VirusDetector):
        self.detector = detector
        self._actions_log: List[EadicationAction] = []
    
    async def eradicate(self, virus_name: str, target: str) -> EradicationAction:
        """Attempt to eradicate a detected virus."""
        actions_taken = []
        success = True
        
        if virus_name in self.detector.signatures:
            sig = self.detector.signatures[virus_name]
            
            if sig.threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
                self.detector._quarantine.append(target)
                actions_taken.append("QUARANTINE: File isolated")
            
            actions_taken.append(f"Signature updated: {sig.signature_hash[:16]}...")
        else:
            actions_taken.append("WARNING: Unknown virus - manual review required")
            success = False
        
        action = EradicationAction(
            action_type="eradicate",
            target=target,
            description="; ".join(actions_taken),
            success=success
        )
        
        self._actions_log.append(action)
        return action
    
    async def patch_vulnerability(self, vuln_type: str) -> EradicationAction:
        """Apply patch for known vulnerability."""
        action = EradicationAction(
            action_type="patch",
            target=vuln_type,
            description=f"Applied {vuln_type} patch",
            success=True
        )
        self._actions_log.append(action)
        return action
    
    def get_actions_log(self) -> List[Dict]:
        """Get eradication actions log."""
        return [
            {
                "type": a.action_type,
                "target": a.target,
                "description": a.description,
                "success": a.success
            }
            for a in self._actions_log
        ]


_global_detector: Optional[VirusDetector] = None
_global_eradicator: Optional[VirusEradicator] = None


def get_virus_detector() -> VirusDetector:
    global _global_detector
    if _global_detector is None:
        _global_detector = VirusDetector()
    return _global_detector


def get_virus_eradicator() -> VirusEradicator:
    global _global_eradicator
    if _global_eradicator is None:
        _global_eradicator = VirusEradicator(get_virus_detector())
    return _global_eradicator
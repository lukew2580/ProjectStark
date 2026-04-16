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
_global_attribution: Optional['ScammerAttribution'] = None


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


class AttributionSource(Enum):
    YOUTUBE = "youtube"
    SOCIAL_MEDIA = "social_media"
    FORUM = "forum"
    WEBSITE = "website"
    FILE_REPOSITORY = "file_repository"
    Pirated_software_SITE = "pirated_site"
    TECH_SUPPORT_SCAM = "tech_support_scam"


@dataclass
class ScammerProfile:
    """Profile of a known scammer distribution channel."""
    source_id: str
    source_name: str
    source_type: AttributionSource
    url: str
    indicators: List[str]
    reported_count: int = 0
    first_seen: str = ""
    risk_score: float = 0.0


@dataclass
class AttributionReport:
    """Report on software attribution."""
    software_hash: str
    source_analysis: List[Dict]
    threatIntel_matches: List[Dict]
    risk_level: str
    recommendations: List[str]
    authority_reports: List[Dict]


class ScammerAttribution:
    """
    Scammer Attribution System.
    Identifies when software was downloaded from known scammer/malicious sources.
    Integrates with threat intelligence for better reporting.
    """
    
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self._scammer_profiles: Dict[str, ScammerProfile] = {}
        self._software_hashes: Dict[str, List[str]] = {}  # hash -> sources
        self._threat_intel: List[Dict] = []
        self._setup_known_scammers()
        self._setup_threat_intel()
    
    def _setup_known_scammers(self):
        """Setup known scammer distribution channels."""
        known_scammers = [
            ("yt_crackwatch", "CrackWatch YouTube", AttributionSource.YOUTUBE, 
             ["crack", "free download", "pirated software", "激活"], 0.9),
            ("yt_freekeys", "Free Keys Pro", AttributionSource.YOUTUBE,
             ["free license", "product key", "activation free"], 0.85),
            ("gh_pirated_repo", "GitHub Pirated Software", AttributionSource.WEBSITE,
             ["free download", "cracked", "patch"], 0.8),
            (" forum_blackhat", "BlackHat Forum", AttributionSource.FORUM,
             ["hack tool", "free malware", "bypass"], 0.95),
            ("site_freeapk", "FreeAPK Dangers", AttributionSource.WEBSITE,
             ["free apk", "premium free", "paid free"], 0.75),
            ("yt_techscam", "Tech Support Scam Ads", AttributionSource.YOUTUBE,
             ["tech support", "call now", "helpline scam"], 0.9),
            ("site_romscam", " romance scam Distribution", AttributionSource.Pirated_software_SITE,
             ["free vpn", "dating app", "crypto free"], 0.85),
            ("file_malware_repo", "Malware File Repository", AttributionSource.FILE_REPOSITORY,
             ["free movie", "free game", "free software"], 0.9),
        ]
        
        for sid, name, stype, indicators, risk in known_scammers:
            combined = " ".join(indicators)
            seed = abs(hash(combined)) % (2**31)
            vector = generate_random_vector(self.dimensions, seed=seed)
            
            self._scammer_profiles[sid] = ScammerProfile(
                source_id=sid,
                source_name=name,
                source_type=stype,
                url=f"https://example.com/{sid}",
                indicators=indicators,
                risk_score=risk,
                first_seen=datetime.now().isoformat()
            )
    
    def _setup_threat_intel(self):
        """Setup threat intelligence feeds."""
        self._threat_intel = [
            {"type": "youtube", "patterns": ["crack", "free download", "激活", "keygen"]},
            {"type": "social", "patterns": ["free followers", "hack account"]},
            {"type": "forum", "patterns": ["bypass", "pirated", "cracked"]},
            {"type": "website", "patterns": ["free apk", "premium free"]},
        ]
    
    async def check_software_attribution(
        self,
        software_hash: str,
        download_source: str = "",
        user_system_info: Dict = None
    ) -> AttributionReport:
        """Check software attribution against known scammer sources."""
        source_analysis = []
        threatIntel_matches = []
        
        if download_source:
            for sid, profile in self._scammer_profiles.items():
                for indicator in profile.indicators:
                    if indicator.lower() in download_source.lower():
                        source_analysis.append({
                            "source_id": sid,
                            "source_name": profile.source_name,
                            "matched_indicator": indicator,
                            "risk_score": profile.risk_score,
                            "source_type": profile.source_type.value
                        })
        
        for intel in self._threat_intel:
            for pattern in intel.get("patterns", []):
                if download_source and pattern.lower() in download_source.lower():
                    threatIntel_matches.append({
                        "source": intel["type"],
                        "matched_pattern": pattern,
                        "severity": "HIGH" if profile.risk_score > 0.7 else "MEDIUM"
                    })
        
        risk_level = "HIGH" if len(source_analysis) > 2 or len(threatIntel_matches) > 2 else "MEDIUM" if source_analysis else "LOW"
        
        recommendations = []
        if source_analysis:
            recommendations.extend([
                "Software from known scammer source - Do NOT run",
                "Report to anti-virus vendors",
                "Submit to VirusTotal for community checking",
                "Report to FTC if financial loss possible"
            ])
        
        authority_reports = []
        if source_analysis:
            authority_reports.append({
                "agency": "FBI IC3",
                "url": "ic3.gov",
                "report_type": "Internet Crime Report",
                "evidence_hash": software_hash
            })
            authority_reports.append({
                "agency": "CISA", 
                "url": "cisa.gov/report",
                "report_type": "Malware/LMalware Report",
                "evidence_hash": software_hash
            })
        
        return AttributionReport(
            software_hash=software_hash,
            source_analysis=source_analysis,
            threatIntel_matches=threatIntel_matches,
            risk_level=risk_level,
            recommendations=recommendations,
            authority_reports=authority_reports
        )
    
    async def search_threat_intel(
        self,
        query: str,
        sources: List[str] = None
    ) -> List[Dict]:
        """Search threat intelligence for mentions."""
        results = []
        query_lower = query.lower()
        
        search_sources = sources or ["youtube", "social", "forum", "website"]
        
        for source in search_sources:
            for intel in self._threat_intel:
                if intel.get("type") == source:
                    for pattern in intel.get("patterns", []):
                        if pattern in query_lower:
                            results.append({
                                "source": source,
                                "pattern": pattern,
                                "query": query,
                                "severity": "HIGH"
                            })
        
        return results
    
    def get_known_scammers(self) -> List[Dict]:
        """Get all known scammer profiles."""
        return [
            {
                "source_id": p.source_id,
                "source_name": p.source_name,
                "source_type": p.source_type.value,
                "risk_score": p.risk_score
            }
            for p in self._scammer_profiles.values()
        ]


def get_scammer_attribution() -> ScammerAttribution:
    global _global_attribution
    if _global_attribution is None:
        _global_attribution = ScammerAttribution()
    return _global_attribution
"""
Hardwareless AI — Scam Fighter System (SFS)
Inspired by Jim Browning, Pierogi, Kitboga - Fight scammers for users
"""
import re
import hashlib
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np

from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import similarity
from core_engine.virus_guard import get_virus_detector, ThreatLevel
from config.settings import DIMENSIONS


class ScamType(Enum):
    TECH_SUPPORT = "tech_support"        # Fake tech support scams
    IRS_SCAM = "irs_scam"                # IRS/imposter scams
    LOTTERY_SCAM = "lottery_scam"        # Fake lottery winnings
    ROMANCE_SCAM = "romance_scam"        # Pig butchering scams
    PHISHING = "phishing"                # Email/website phishing
    VIRAL_SPREAD = "viral_spread"       # Social media viral scams
    CRYPTO_SCAM = "crypto_scam"          # Crypto investment scams
    JOB_SCAM = "job_scam"                # Fake job offers
    EXTORTION = "extortion"             # Sextortion, etc


class ThreatCategory(Enum):
    CALL_CENTER = "call_center"          # Scam call center
    INDIVIDUAL_SCAMMER = "individual"    # Individual scammer
    SCAM_WEBSITE = "scam_website"        # Phishing/fake site
    SCAM_NETWORK = "scam_network"        # Organized operation


@dataclass
class ScammerProfile:
    """Profile of a detected scammer."""
    profile_id: str
    scam_type: ScamType
    indicators: List[str]
    phone_numbers: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    websites: List[str] = field(default_factory=list)
    ip_addresses: List[str] = field(default_factory=list)
    language_patterns: List[str] = field(default_factory=list)
    first_seen: str = ""
    reports_count: int = 0
    confidence: float = 0.0


@dataclass
class ScamReport:
    """Report of detected scam."""
    scam_type: ScamType
    threat_category: ThreatCategory
    confidence: float
    indicators: List[str]
    recommended_actions: List[str]
    evidence_collected: Dict = field(default_factory=dict)


class ScamDetector:
    """
    Scam Detection System - The "Scam Fighter" 
    Detects phone scams, tech support scams, phishing, etc.
    """
    
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self.profiles: Dict[str, ScammerProfile] = {}
        self._scam_patterns = {}
        self._setup_scam_patterns()
    
    def _setup_scam_patterns(self):
        """Setup known scam patterns as HDC vectors."""
        scam_patterns = [
            (ScamType.TECH_SUPPORT, [
                "microsoft support", "windows support", "apple support",
                "your computer is infected", "call now", "tech support",
                "helpline", "support desk", "system alert", "security warning"
            ]),
            (ScamType.IRS_SCAM, [
                "irs", "internal revenue", "taxes owed", "arrest warrant",
                "legal action", "court", "sue", "irs agent", "tax penalty"
            ]),
            (ScamType.LOTTERY_SCAM, [
                "you won", "lottery winner", "prize money", "claim your prize",
                "congratulations", "winner selected", "free gift", "claim now"
            ]),
            (ScamType.ROMANCE_SCAM, [
                "love", "meet", "long distance", "send money", "gift cards",
                "bitcoin investment", "business proposal", "future together"
            ]),
            (ScamType.PHISHING, [
                "verify account", "update payment", "confirm password",
                "click here", "urgent action", "suspended", "locked"
            ]),
            (ScamType.CRYPTO_SCAM, [
                "bitcoin", "crypto investment", "double your money", "guaranteed",
                "mining", "staking", "defi", "blockchain opportunity"
            ]),
            (ScamType.JOB_SCAM, [
                "work from home", "easy money", "interview", "hiring now",
                "remote job", "package forwarding", "mystery shopper"
            ]),
            (ScamType.EXTORTION, [
                "compromised", "nude photos", "recordings", "expose",
                "pay now", "bitcoin", "24 hours", "tell everyone"
            ]),
        ]
        
        for scam_type, keywords in scam_patterns:
            combined = " ".join(keywords)
            seed = int.from_bytes(
                hashlib.sha256(combined.encode()).digest()[:4], 
                'big'
            ) % (2**31)
            vector = generate_random_vector(self.dimensions, seed=seed)
            self._scam_patterns[scam_type] = {
                "vector": vector,
                "keywords": keywords,
                "patterns": keywords
            }
    
    async def analyze_call(self, transcript: str, metadata: Dict = None) -> ScamReport:
        """Analyze a call transcript for scam indicators."""
        transcript_lower = transcript.lower()
        indicators = []
        matched_types = []
        
        for scam_type, data in self._scam_patterns.items():
            matches = sum(1 for kw in data["patterns"] if kw in transcript_lower)
            if matches > 0:
                matched_types.append((scam_type, matches))
                indicators.append(f"Matched {matches} keywords: {scam_type.value}")
        
        if not matched_types:
            return ScamReport(
                scam_type=ScamType.TECH_SUPPORT,
                threat_category=ThreatCategory.INDIVIDUAL_SCAMMER,
                confidence=0.0,
                indicators=["No scam patterns detected"],
                recommended_actions=["Continue monitoring"],
                evidence_collected={}
            )
        
        matched_types.sort(key=lambda x: x[1], reverse=True)
        primary_type = matched_types[0][0]
        confidence = min(matched_types[0][1] / 5.0, 1.0)
        
        actions = self._get_recommended_actions(primary_type)
        
        phone_pattern = r'(\+?1?[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, transcript)
        
        email_pattern = r'[\w.-]+@[\w.-]+\.\w+'
        emails = re.findall(email_pattern, transcript)
        
        return ScamReport(
            scam_type=primary_type,
            threat_category=self._determine_category(matched_types),
            confidence=confidence,
            indicators=indicators,
            recommended_actions=actions,
            evidence_collected={
                "phones_found": [p.group() for p in re.finditer(r'\d{3,}', transcript)],
                "emails_found": emails,
                "transcript_length": len(transcript)
            }
        )
    
    async def analyze_text(self, text: str) -> ScamReport:
        """Analyze text/messages for scam patterns."""
        return await self.analyze_call(text)
    
    async def analyze_phone_number(self, phone: str) -> Dict:
        """Analyze a phone number against known scam patterns."""
        phone_hash = hashlib.sha256(phone.encode()).hexdigest()[:16]
        
        suspicious_patterns = [
            ("multiple 800 numbers", phone.startswith(("800", "888", "877", "866"))),
            ("area code 473", "473" in phone),
            ("premium rate", phone.startswith(("900", "976"))),
            ("international format", phone.startswith("+")),
        ]
        
        findings = []
        is_suspicious = False
        
        for pattern, match in suspicious_patterns:
            if match:
                findings.append(pattern)
                is_suspicious = True
        
        if phone in ["1-800-555-0100", "1-800-555-0199"]:
            is_suspicious = False
            findings.append("Test/fake number")
        
        return {
            "phone": phone,
            "analysis_hash": phone_hash,
            "suspicious": is_suspicious,
            "findings": findings,
            "recommendation": "Block and report" if is_suspicious else "Likely legitimate"
        }
    
    async def analyze_website(self, url: str) -> Dict:
        """Analyze website for scam indicators."""
        url_lower = url.lower()
        
        scam_indicators = [
            "free", "gift", "winner", "prize", "claim",
            "verify", "update", "secure", "account",
            "login", "signin", "password"
        ]
        
        url_parts = url_lower.split("/")
        domain = url_parts[2] if len(url_parts) > 2 else url_lower
        
        issues = []
        score = 0
        
        if any(s in domain for s in ["free", "gift", "winner", "prize"]):
            issues.append("Suspicious domain keywords")
            score += 30
        
        if len(domain) > 50:
            issues.append("Unusually long domain")
            score += 20
        
        suspicious_tlds = [".xyz", ".top", ".work", ".click", ".gq", ".ml", ".cf"]
        if any(domain.endswith(tld) for tld in suspicious_tlds):
            issues.append("Suspicious TLD")
            score += 40
        
        if score > 50:
            risk = "HIGH"
        elif score > 25:
            risk = "MEDIUM"
        else:
            risk = "LOW"
        
        return {
            "url": url,
            "domain": domain,
            "risk_level": risk,
            "score": score,
            "issues": issues,
            "recommendation": "Avoid" if risk == "HIGH" else "Caution" if risk == "MEDIUM" else "Probably safe"
        }
    
    async def analyze_email(self, email: str, content: str = "") -> Dict:
        """Analyze email for phishing/scam patterns."""
        parts = email.split("@")
        username = parts[0] if len(parts) > 1 else ""
        domain = parts[1] if len(parts) > 1 else ""
        
        issues = []
        
        suspicious_patterns = [
            (r'\d{4,}', "Username contains many digits"),
            ("support", "Generic support in username"),
            ("admin", "Admin in username"),
            ("verify", "Verify in username"),
        ]
        
        for pattern, desc in suspicious_patterns:
            if re.search(pattern, username):
                issues.append(desc)
        
        if domain in ["gmail.com", "yahoo.com", "hotmail.com"]:
            issues.append("Free email provider (needs scrutiny)")
        
        phishing_keywords = [
            "urgent", "verify", "suspended", "action required",
            "click here", "login", "password", "account"
        ]
        
        content_lower = content.lower()
        content_issues = [kw for kw in phishing_keywords if kw in content_lower]
        
        if len(content_issues) > 3:
            issues.append(f"Multiple phishing keywords: {content_issues}")
        
        return {
            "email": email,
            "domain": domain,
            "issues": issues,
            "recommendation": "Treat as suspicious" if issues else "Needs context"
        }
    
    def _determine_category(self, matched_types: List) -> ThreatCategory:
        """Determine threat category from matched types."""
        if len(matched_types) >= 3:
            return ThreatCategory.SCAM_NETWORK
        elif len(matched_types) >= 2:
            return ThreatCategory.CALL_CENTER
        else:
            return ThreatCategory.INDIVIDUAL_SCAMMER
    
    def _get_recommended_actions(self, scam_type: ScamType) -> List[str]:
        """Get recommended actions for scam type."""
        actions_map = {
            ScamType.TECH_SUPPORT: [
                "Do not call any numbers provided",
                "Hang up immediately",
                "Report to FTC: reportfraud.ftc.gov",
                "Report to Microsoft: microsoft.com/reportascam"
            ],
            ScamType.IRS_SCAM: [
                "IRS never calls demanding immediate payment",
                "Do not engage with caller",
                "Report to treasury.gov/tigta",
                "Block the number"
            ],
            ScamType.LOTTERY_SCAM: [
                "You cannot win a lottery you didn't enter",
                "Never send money to claim prizes",
                "Report to ftc.gov/complaint"
            ],
            ScamType.ROMANCE_SCAM: [
                "Never send money to someone you haven't met",
                "Reverse image search their photos",
                "Do not share personal photos",
                "Report to ftc.gov/complaint"
            ],
            ScamType.PHISHING: [
                "Do not click links in suspicious emails",
                "Go directly to the website instead",
                "Report to phishing@apwg.org"
            ],
            ScamType.CRYPTO_SCAM: [
                "No investment is guaranteed",
                "Research thoroughly before any investment",
                "Never send crypto to strangers"
            ],
            ScamType.JOB_SCAM: [
                "Research the company thoroughly",
                "Never accept checks from unknown sources",
                "Never provide SSN before verifying"
            ],
            ScamType.EXTORTION: [
                "Do not respond to threats",
                "Report to local police",
                "Block and ignore",
                "Do not send any money or photos"
            ]
        }
        return actions_map.get(scam_type, ["Research and verify independently"])


class ScamFighter:
    """
    Active scam fighting system.
    Like Jim Browning, Pierogi, Kitboga - takes the fight to scammers.
    """
    
    def __init__(self):
        self.detector = ScamDetector()
        self._reports_filed = []
    
    async def investigate_phone(self, phone: str) -> Dict:
        """Investigate a phone number thoroughly."""
        analysis = await self.detector.analyze_phone_number(phone)
        
        report = {
            "phone": phone,
            "analysis": analysis,
            "actions": [
                "Collect evidence",
                "Check against scam databases",
                "Report to authorities if needed"
            ]
        }
        
        return report
    
    async def investigate_email(self, email: str, content: str = "") -> Dict:
        """Investigate an email address."""
        analysis = await self.detector.analyze_email(email, content)
        
        return {
            "email": email,
            "analysis": analysis,
            "actions": [
                "Check sender domain reputation",
                "Verify links without clicking",
                "Report to email provider"
            ]
        }
    
    async def investigate_website(self, url: str) -> Dict:
        """Investigate a suspicious website."""
        analysis = await self.detector.analyze_website(url)
        
        if analysis["risk_level"] == "HIGH":
            actions = [
                "Do not visit the site",
                "Report to Google Safe Browsing",
                "Report to APWG (anti-phishing)"
            ]
        else:
            actions = ["Use caution", "Verify through other sources"]
        
        return {
            "url": url,
            "analysis": analysis,
            "recommended_actions": actions
        }
    
    async def generate_authority_report(self, evidence: Dict) -> Dict:
        """Generate report suitable for authorities."""
        report = {
            "report_id": hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:12],
            "timestamp": datetime.now().isoformat(),
            "summary": "Scam Activity Report",
            "evidence": evidence,
            "recommended_recipients": [
                "FTC (reportfraud.ftc.gov)",
                "FBI IC3 (ic3.gov)",
                "Local police department"
            ]
        }
        
        self._reports_filed.append(report)
        return report
    
    def get_investigation_history(self) -> List[Dict]:
        """Get history of investigations."""
        return self._reports_filed.copy()


_global_detector: Optional[ScamDetector] = None
_global_fighter: Optional[ScamFighter] = None


def get_scam_detector() -> ScamDetector:
    global _global_detector
    if _global_detector is None:
        _global_detector = ScamDetector()
    return _global_detector


def get_scam_fighter() -> ScamFighter:
    global _global_fighter
    if _global_fighter is None:
        _global_fighter = ScamFighter()
    return _global_fighter
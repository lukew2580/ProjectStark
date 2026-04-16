"""
Hardwareless AI — Scam Fighter API Routes
SFS: Fight scammers like Jim Browning, Pierogi, Kitboga
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/scam", tags=["scam"])


class AnalyzeCallRequest(BaseModel):
    transcript: str
    metadata: Optional[Dict[str, Any]] = None


class AnalyzeTextRequest(BaseModel):
    text: str


class AnalyzePhoneRequest(BaseModel):
    phone: str


class AnalyzeWebsiteRequest(BaseModel):
    url: str


class AnalyzeEmailRequest(BaseModel):
    email: str
    content: Optional[str] = ""


class AuthorityReportRequest(BaseModel):
    evidence: Dict[str, Any]


@router.get("/status")
async def get_scam_status():
    """Get scam fighter system status."""
    from core_engine.scam_fighter import get_scam_detector, get_scam_fighter
    
    detector = get_scam_detector()
    fighter = get_scam_fighter()
    
    return {
        "system": "SFS",
        "name": "Scam Fighter System",
        "scam_types": [s.value for s in detector._scam_patterns.keys()],
        "investigations": len(fighter.get_investigation_history())
    }


@router.post("/analyze/call")
async def analyze_call(request: AnalyzeCallRequest):
    """Analyze a call transcript for scam patterns."""
    from core_engine.scam_fighter import get_scam_detector
    
    detector = get_scam_detector()
    report = await detector.analyze_call(request.transcript, request.metadata)
    
    return {
        "scam_type": report.scam_type.value,
        "threat_category": report.threat_category.value,
        "confidence": report.confidence,
        "indicators": report.indicators,
        "recommended_actions": report.recommended_actions,
        "evidence_collected": report.evidence_collected
    }


@router.post("/analyze/text")
async def analyze_text(request: AnalyzeTextRequest):
    """Analyze text/messages for scam patterns."""
    from core_engine.scam_fighter import get_scam_detector
    
    detector = get_scam_detector()
    report = await detector.analyze_text(request.text)
    
    return {
        "scam_type": report.scam_type.value,
        "confidence": report.confidence,
        "indicators": report.indicators,
        "recommended_actions": report.recommended_actions
    }


@router.post("/analyze/phone")
async def analyze_phone(request: AnalyzePhoneRequest):
    """Investigate a phone number."""
    from core_engine.scam_fighter import get_scam_fighter
    
    fighter = get_scam_fighter()
    result = await fighter.investigate_phone(request.phone)
    
    return result


@router.post("/analyze/website")
async def analyze_website(request: AnalyzeWebsiteRequest):
    """Investigate a suspicious website."""
    from core_engine.scam_fighter import get_scam_fighter
    
    fighter = get_scam_fighter()
    result = await fighter.investigate_website(request.url)
    
    return result


@router.post("/analyze/email")
async def analyze_email(request: AnalyzeEmailRequest):
    """Investigate an email for phishing."""
    from core_engine.scam_fighter import get_scam_fighter
    
    fighter = get_scam_fighter()
    result = await fighter.investigate_email(request.email, request.content or "")
    
    return result


@router.post("/report/authority")
async def generate_authority_report(request: AuthorityReportRequest):
    """Generate report for authorities (FTC, FBI, etc)."""
    from core_engine.scam_fighter import get_scam_fighter
    
    fighter = get_scam_fighter()
    report = await fighter.generate_authority_report(request.evidence)
    
    return report


@router.get("/scam/types")
async def list_scam_types():
    """List all supported scam types."""
    from core_engine.scam_fighter import ScamType
    
    scam_info = {
        "tech_support": {
            "name": "Tech Support Scam",
            "description": "Fake Microsoft/Apple support calling about 'infected' computers",
            "examples": ["Your computer has a virus", "Call now for immediate help"]
        },
        "irs_scam": {
            "name": "IRS Scam", 
            "description": "Imposter claiming you owe taxes and will be arrested",
            "examples": ["IRS has issued arrest warrant", "Pay now or face legal action"]
        },
        "lottery_scam": {
            "name": "Lottery/Prize Scam",
            "description": "You've won a lottery you never entered",
            "examples": ["Congratulations! You won $5 million", "Claim your prize now"]
        },
        "romance_scam": {
            "name": "Romance Scam (Pig Butchering)",
            "description": "Long-term con building fake relationship for crypto investment",
            "examples": ["I love you", "Invest in this opportunity for our future"]
        },
        "phishing": {
            "name": "Phishing",
            "description": "Fake emails trying to steal credentials",
            "examples": ["Verify your account", "Your account has been suspended"]
        },
        "crypto_scam": {
            "name": "Crypto Scam",
            "description": "Fake crypto investment opportunities",
            "examples": ["Guaranteed 10x returns", "Double your Bitcoin"]
        },
        "job_scam": {
            "name": "Job Scam",
            "description": "Fake job offers requiring personal info or money",
            "examples": ["Work from home", "Package forwarding job"]
        },
        "extortion": {
            "name": "Extortion",
            "description": "Threatening to expose personal info/photos",
            "examples": ["I have your recordings", "Pay in 24 hours or I tell everyone"]
        }
    }
    
    return {
        "scam_types": [s.value for s in ScamType],
        "info": scam_info
    }


@router.get("/resources")
async def get_resources():
    """Get scam reporting resources."""
    return {
        "authorities": [
            {"name": "FTC", "url": "https://reportfraud.ftc.gov", "description": "Federal Trade Commission"},
            {"name": "FBI IC3", "url": "https://www.ic3.gov", "description": "Internet Crime Complaint Center"},
            {"name": "FCC", "url": "https://www.fcc.gov/complaints", "description": "Unwanted calls/texts"},
            {"name": "Do Not Call", "url": "https://www.donotcall.gov", "description": "Register your number"}
        ],
        "company_reporting": [
            {"company": "Microsoft", "url": "microsoft.com/reportascam"},
            {"company": "Apple", "url": "reportphishing@apple.com"},
            {"company": "Google", "url": "https://safebrowsing.google.com/safebrowsing/report_phish/"}
        ],
        "tips": [
            "Never give remote access to your computer to unknown callers",
            "IRS never calls demanding immediate payment",
            "You cannot win a lottery you didn't enter",
            "Never send money to someone you haven't met in person",
            "Hang up on pressure tactics - legitimate businesses don't rush you"
        ]
    }
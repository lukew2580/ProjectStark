"""
Hardwareless AI — Evidence & Legal Routes
Evidence collection with chain of custody for legal proceedings
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/v1/evidence", tags=["evidence"])


class CollectEvidenceRequest(BaseModel):
    evidence_type: str  # phone_record, email_content, website_screenshot, etc
    content: Dict      # The evidence content
    source_info: Dict  # Source details (phone number, URL, etc)


class VerifyEvidenceRequest(BaseModel):
    evidence_id: str


class GenerateReportRequest(BaseModel):
    evidence_ids: List[str]
    authority: str  # FTC, FBI_IC3, FCC
    summary: str
    recommended_action: str


@router.get("/status")
async def get_evidence_status():
    """Get evidence collector status."""
    from core_engine.evidence import get_evidence_collector
    
    collector = get_evidence_collector()
    return {
        "total_evidence": len(collector._evidence),
        "total_reports": len(collector._reports),
        "integrity_verified": sum(1 for e in collector._evidence.values() if e.integrity.value == "verified"),
        "submitted_count": sum(1 for e in collector._evidence.values() if e.submitted_to)
    }


@router.post("/collect")
async def collect_evidence(request: CollectEvidenceRequest):
    """Collect evidence with chain of custody."""
    from core_engine.evidence import get_evidence_collector, EvidenceType
    
    try:
        ev_type = EvidenceType(request.evidence_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid evidence_type")
    
    collector = get_evidence_collector()
    record = collector.collect_evidence(ev_type, request.content, request.source_info)
    
    return {
        "evidence_id": record.evidence_id,
        "content_hash": record.content_hash,
        "timestamp": record.timestamp_utc,
        "integrity": record.integrity.value,
        "chain_length": len(record.chain_of_custody)
    }


@router.post("/verify/{evidence_id}")
async def verify_evidence_integrity(evidence_id: str):
    """Verify evidence integrity (SHA-256 hash check)."""
    from core_engine.evidence import get_evidence_collector
    
    collector = get_evidence_collector()
    verified = collector.verify_integrity(evidence_id)
    
    return {
        "evidence_id": evidence_id,
        "verified": verified,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/list")
async def list_evidence():
    """List all collected evidence."""
    from core_engine.evidence import get_evidence_collector
    
    collector = get_evidence_collector()
    return {"evidence": collector.get_all_evidence()}


@router.get("/{evidence_id}")
async def get_evidence_detail(evidence_id: str):
    """Get detailed evidence record."""
    from core_engine.evidence import get_evidence_collector
    
    collector = get_evidence_collector()
    record = collector.get_evidence(evidence_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    return {
        "id": record.evidence_id,
        "type": record.evidence_type.value,
        "content_hash": record.content_hash,
        "timestamp": record.timestamp_utc,
        "source_info": record.source_info,
        "chain_of_custody": record.chain_of_custody,
        "integrity": record.integrity.value,
        "submitted_to": record.submitted_to
    }


@router.post("/report/generate")
async def generate_authority_report(request: GenerateReportRequest):
    """Generate legal report for authorities."""
    from core_engine.evidence import get_evidence_collector
    
    collector = get_evidence_collector()
    report = collector.generate_authority_report(
        evidence_ids=request.evidence_ids,
        report_type=request.authority,
        summary=request.summary,
        recommended_action=request.recommended_action
    )
    
    return {
        "report_id": report.report_id,
        "authority": report.report_type,
        "generated_at": report.generated_at,
        "evidence_count": len(report.evidence_ids),
        "chain_verified": report.chain_verified
    }


@router.get("/reports")
async def list_reports():
    """List all generated reports."""
    from core_engine.evidence import get_evidence_collector
    
    collector = get_evidence_collector()
    return {"reports": collector.get_reports()}


@router.post("/format/{authority}")
async def format_for_authority(authority: str, evidence_ids: List[str]):
    """Format evidence for specific authority."""
    from core_engine.evidence import get_evidence_collector, get_legal_reporter
    
    collector = get_evidence_collector()
    reporter = get_legal_reporter()
    
    formatted = reporter.format_for_authority(evidence_ids, authority, collector)
    
    return formatted


@router.post("/submit/package")
async def generate_submission_package(authority: str, evidence_ids: List[str]):
    """Generate complete submission package for authority."""
    from core_engine.evidence import get_evidence_collector, get_legal_reporter
    
    collector = get_evidence_collector()
    reporter = get_legal_reporter()
    
    package = reporter.generate_submission_package(evidence_ids, authority, collector)
    
    return package


from datetime import datetime
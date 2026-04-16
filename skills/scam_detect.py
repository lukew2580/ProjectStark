"""
Scam Detect Skill — Detects phone/email/website scams
"""
from typing import Dict, Any

async def run(context: Dict, args: Dict) -> Dict[str, Any]:
    from core_engine.scam_fighter import get_scam_detector
    
    detector = get_scam_detector()
    
    phone = args.get("phone", "")
    email = args.get("email", "")
    website = args.get("website", "")
    
    if phone:
        result = await detector.analyze_phone_number(phone)
        return {"type": "phone", "result": result}
    
    if email:
        result = await detector.analyze_email(email, args.get("content", ""))
        return {"type": "email", "result": result}
    
    if website:
        result = await detector.analyze_website(website)
        return {"type": "website", "result": result}
    
    return {"error": "phone, email, or website required"}

meta = {
    "name": "scam_detect",
    "description": "Analyzes phone/email/website for scam patterns",
    "args": {"phone": "phone number", "email": "email address", "website": "URL"},
    "triggers": ["scam", "fake", "phishing", "spam", "suspect"]
}